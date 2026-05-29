export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <h1 className="text-3xl font-bold text-white">
        Hardware Price Tracker
      </h1>
      <p className="text-gray-400">
        Отслеживание цен на GPU, CPU, RAM
      </p>
      <div className="flex gap-3 mt-4">
        <div className="px-4 py-2 bg-gray-800 rounded-lg text-sm text-gray-300">
          🚧 Dashboard — в разработке
        </div>
        <a
          href="/monitor"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm text-white transition-colors"
        >
          ETL Monitor →
        </a>
      </div>
    </div>
  );
}
