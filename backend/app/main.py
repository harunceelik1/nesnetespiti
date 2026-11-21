from contextlib import asynccontextmanager
from base64 import b64encode
from io import BytesIO

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from PIL import Image, UnidentifiedImageError

from .models.base_detector import DetectorError
from .models.detector_registry import DetectorRegistry
from .services.inference_orchestrator import run_detection
from .services.inventory_service import detect_raw_queries
from .services.query_processor import process_query
from .services.translation_service import TranslationService, TranslationServiceError
from .utils.visualization import annotate_image


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Her sunucu süreci için bir kez yüklenir; istekler aynı servisi kullanır.
    app.state.translation_service = TranslationService()
    app.state.detector_registry = DetectorRegistry()
    yield
    del app.state.detector_registry
    del app.state.translation_service


app = FastAPI(title="Open-Vocabulary Object Detection", lifespan=lifespan)

# Yalnızca yerel Next.js geliştirme arayüzüne erişim izni verilir.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    expose_headers=["X-Model", "X-Device", "X-Inference-Time-Ms", "X-Adaptive-Threshold-Used", "X-Threshold-Selection-Reason"],
)


@app.exception_handler(TranslationServiceError)
async def translation_error_handler(request: Request, exc: TranslationServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.exception_handler(DetectorError)
async def detector_error_handler(request: Request, exc: DetectorError):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.get("/models")
def models(request: Request):
    return {"models": request.app.state.detector_registry.list_models()}


@app.get("/health")
def health():
    return {"status": "ok"}


def prepare_detection(request: Request, original_query: str, model: str, english_query: str | None = None):
    # Geçersiz form değerini pahalı çeviriden önce reddet; henüz model seçilmez.
    request.app.state.detector_registry.validate_id(model)
    # Çeviri/query işleme detector seçilmeden önce tek ortak noktada yapılır.
    # english_query: arayüzde kullanıcının düzelttiği İngilizce ifade (çeviriyi atlar).
    plan = process_query(original_query, request.app.state.translation_service, english_query)
    return request.app.state.detector_registry.get(model), plan


def render_detection_jpeg(image: Image.Image, detections: list) -> bytes:
    """JSON ve JPEG endpoint'i aynı çizim kodunu, hazır detection listesini kullanır."""
    with annotate_image(image, detections) as annotated, BytesIO() as buffer:
        annotated.save(buffer, format="JPEG")
        return buffer.getvalue()


@app.post("/detect")
def detect(
    request: Request,
    image: UploadFile = File(...),
    query: str = Form(...),
    threshold: float = Form(0.2, ge=0.0, le=1.0),
    model: str = Form("owlvit"),
    english_query: str | None = Form(None),
    include_image: bool = Form(False),
):
    # File ve Form parametreleri multipart/form-data olarak alınır.
    # Senkron endpoint, ağır model işlemini FastAPI'nin iş parçacığında çalıştırır.
    try:
        original_query = query
        query = query.strip()
        if not query:
            raise HTTPException(status_code=422, detail="query boş olamaz.")

        detector, plan = prepare_detection(request, original_query, model, english_query)

        try:
            with Image.open(image.file) as source:
                rgb_image = source.convert("RGB")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise HTTPException(
                status_code=400, detail="Geçerli bir görsel dosyası yükleyin."
            ) from exc

        with rgb_image:
            # Eski threshold form alanı kabul edilir; normal akışta model bazlı
            # adaptive politika seçer. Sabit eşik raw debug endpoint'inde korunur.
            detection_result = run_detection(detector, rgb_image, plan)
            payload = {"query": query, **detection_result}
            if include_image:
                # Ek inference yok: metadata içindeki kutuların aynısı çizilir.
                payload["annotated_image"] = {
                    "media_type": "image/jpeg",
                    "data_base64": b64encode(render_detection_jpeg(
                        rgb_image, detection_result["detections"]
                    )).decode("ascii"),
                }

        return payload
    finally:
        image.file.close()


@app.post(
    "/detect-image",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}, "description": "Tespit görseli"}},
)
def detect_image(
    request: Request,
    image: UploadFile = File(...),
    query: str = Form(...),
    threshold: float = Form(0.2, ge=0.0, le=1.0),
    model: str = Form("owlvit"),
    english_query: str | None = Form(None),
):
    # JSON endpoint'i ile aynı model servisi ve form parametreleri kullanılır.
    try:
        query = query.strip()
        if not query:
            raise HTTPException(status_code=422, detail="query boş olamaz.")

        detector, plan = prepare_detection(request, query, model, english_query)

        try:
            with Image.open(image.file) as source:
                rgb_image = source.convert("RGB")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise HTTPException(
                status_code=400, detail="Geçerli bir görsel dosyası yükleyin."
            ) from exc

        with rgb_image:
            detection_result = run_detection(detector, rgb_image, plan)
            jpeg_bytes = render_detection_jpeg(rgb_image, detection_result["detections"])

        return Response(
            content=jpeg_bytes, media_type="image/jpeg",
            headers={
                "X-Model": detection_result["model_id"],
                "X-Device": detection_result["device"],
                "X-Inference-Time-Ms": str(detection_result["inference_time_ms"]),
                "X-Adaptive-Threshold-Used": str(detection_result.get("adaptive_threshold_used", "")),
                "X-Threshold-Selection-Reason": detection_result["threshold_selection_reason"],
            },
        )
    finally:
        image.file.close()


@app.post(
    "/detect-raw-image",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}, "description": "Ham tespit görseli"}},
)
def detect_raw_image(
    request: Request,
    image: UploadFile = File(...),
    query: str = Form(...),
    threshold: float = Form(0.2, ge=0.0, le=1.0),
    model: str = Form("owlvit"),
    english_query: str | None = Form(None),
):
    try:
        query = query.strip()
        if not query:
            raise HTTPException(status_code=422, detail="query boş olamaz.")

        detector, plan = prepare_detection(request, query, model, english_query)
        try:
            with Image.open(image.file) as source:
                rgb_image = source.convert("RGB")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise HTTPException(
                status_code=400, detail="Geçerli bir görsel dosyası yükleyin."
            ) from exc

        with rgb_image:
            # Aynı model kullanılır; confidence filtresinden sonra kutu elemesi yapılmaz.
            detections = detect_raw_queries(detector,
                rgb_image, plan, threshold
            )
            with annotate_image(rgb_image, detections) as annotated:
                with BytesIO() as buffer:
                    annotated.save(buffer, format="JPEG")
                    jpeg_bytes = buffer.getvalue()

        return Response(content=jpeg_bytes, media_type="image/jpeg")
    finally:
        image.file.close()
