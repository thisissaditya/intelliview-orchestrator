"use client";
import { useRouter } from "next/navigation";

export default function ScheduleInterviewButton({ candidateId }) {
  const router = useRouter();

  return (
    <button
      onClick={() => router.push(`/interview?candidateId=${candidateId}`)}
      className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
    >
      Schedule Interview
    </button>
  );
}