import PriceChart from "@/components/PriceChart";

export default function TestChartPage() {
  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-xl font-semibold text-white mb-6">
        Тест графика — NVIDIA GeForce RTX 4090
      </h1>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="mb-4">
          <div className="text-lg font-medium text-white">NVIDIA GeForce RTX 4090</div>
          <div className="text-sm text-gray-400">GPU · MSRP $1,599</div>
        </div>

        <PriceChart
          data={[]}          // пустой массив → покажет MOCK_DATA
          msrp={1599}
        />
      </div>
    </div>
  );
}
