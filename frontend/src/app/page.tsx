import DetectionWorkspace from "@/components/detection-workspace";

export default function HomePage() {
  return (
    <main className="application">
      <header className="app-header">
        <h1>Open Vocabulary Detection</h1>
        <p>Natural language object detection workspace</p>
      </header>
      <DetectionWorkspace />
    </main>
  );
}
