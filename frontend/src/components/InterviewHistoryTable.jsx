// frontend/src/components/InterviewHistoryTable.jsx

const statusStyles = {
  completed: "bg-green-100 text-green-700",
  pending: "bg-yellow-100 text-yellow-700",
  in_progress: "bg-blue-100 text-blue-700",
  flagged: "bg-red-100 text-red-700",
};

const riskStyles = {
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-red-100 text-red-700",
};

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function InterviewHistoryTable({ interviews = [] }) {
  if (interviews.length === 0) {
    return (
      <div className="text-gray-500 text-sm py-6 text-center border rounded-md">
        No interviews yet.
      </div>
    );
  }

  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b text-left text-gray-500">
          <th className="py-2 px-3">Session ID</th>
          <th className="py-2 px-3">Date</th>
          <th className="py-2 px-3">Status</th>
          <th className="py-2 px-3">Score</th>
          <th className="py-2 px-3">Risk Level</th>
        </tr>
      </thead>
      <tbody>
        {interviews.map((iv) => (
          <tr key={iv.session_id} className="border-b hover:bg-gray-50">
            <td className="py-2 px-3 font-mono text-xs">{iv.session_id}</td>
            <td className="py-2 px-3">{formatDate(iv.date)}</td>
            <td className="py-2 px-3">
              <span className={`px-2 py-1 rounded-full text-xs ${statusStyles[iv.status] || "bg-gray-100 text-gray-700"}`}>
                {iv.status}
              </span>
            </td>
            <td className="py-2 px-3">{iv.score ?? "—"}</td>
            <td className="py-2 px-3">
              <span className={`px-2 py-1 rounded-full text-xs ${riskStyles[iv.risk_level] || "bg-gray-100 text-gray-700"}`}>
                {iv.risk_level}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}