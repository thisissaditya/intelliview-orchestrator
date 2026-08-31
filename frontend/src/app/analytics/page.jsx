"use client";

import { useMemo, useState, useCallback } from "react";
import useSWR from "swr";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
  Legend,
  Line,
  LineChart,
} from "recharts";

import {
  Download,
  Calendar,
  Filter,
} from "lucide-react";


import Card from "@/components/Card";
import Stat from "@/components/Stat";
import { Badge } from "@/components/Badge";
import { Skeleton, ErrorState } from "@/components/States";

import { toast } from "@/lib/toast";
import { cn } from "@/lib/utils";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { exportAnalyticsCSV, exportAnalyticsPDF } from "@/lib/export";



const RISK_BUCKETS = [
  { name: "Low (<0.3)", color:"#10b981" },
  { name: "Medium (0.3-0.6)", color:"#f59e0b" },
  { name: "High (0.6-0.8)", color:"#f97316" },
  { name: "Critical (≥0.8)", color:"#ef4444" },
];


const DATE_PRESETS=[
 {
  label:"All time",
  value:"all"
 },
 {
  label:"Last 24h",
  value:"24h"
 },
 {
  label:"Last 7d",
  value:"7d"
 },
 {
  label:"Last 30d",
  value:"30d"
 }
];


const TOOLTIP_STYLE={
 contentStyle:{
  background:"#12121a",
  border:"1px solid #27272a",
  borderRadius:8
 }
};




function filterByDate(sessions,range){

 if(range==="all")
 return sessions;


 const now=Date.now();

 const msMap = {
  "24h": 86400000,
  "7d": 604800000,
  "30d": 2592000000,
};

const ms = msMap[range];

if (typeof ms !== "number") {
  return sessions;
}

return sessions.filter((s) => {

 const t=new Date(
 s.updated_at ||
 s.created_at ||
 0
 ).getTime();


 return now-t<=ms;

 });


}






function RiskDistribution({
 sessions,
 loading,
 onDrillDown
}){


 const buckets=useMemo(()=>{


 const counts=RISK_BUCKETS.map(
 b=>({...b,value:0})
 );


 sessions.forEach((s)=>{


 const r=s?.risk_score;


 if (typeof r !== "number" || Number.isNaN(r)) {
  return;
}

 if(r<0.3)
 counts[0].value++;

 else if(r<0.6)
 counts[1].value++;

 else if(r<0.8)
 counts[2].value++;

 else
 counts[3].value++;


 });


 return counts;


 },[sessions]);



 return(

 <Card
 title="Risk distribution"
 description="Sessions bucketed by final risk score."
 action={
 <button
 onClick={()=>onDrillDown("risk")}
 className="flex items-center gap-1 rounded-md border border-border bg-bg-card px-2 py-1 text-xs"
 >
 <Filter size={12}/>
 Drill down
 </button>
 }
 >


 {
 loading ?

 <Skeleton className="h-64 w-full"/>


 :

 buckets.every(
 b=>b.value===0
 )

 ?

 <div className="py-8 text-center text-sm text-muted">
 No sessions with risk scores yet.
 </div>


 :

 <ResponsiveContainer
 width="100%"
 height={280}
 >

 <PieChart>

 <Pie
 data={buckets}
 dataKey="value"
 nameKey="name"
 cx="50%"
 cy="50%"
 outerRadius={90}
 innerRadius={50}
 >

 {
 buckets.map((b,i)=>(

 <Cell
 key={i}
 fill={b.color}
 />

 ))
 }


 </Pie>


 <Tooltip {...TOOLTIP_STYLE}/>

 <Legend/>


 </PieChart>


 </ResponsiveContainer>


 }



 </Card>


 );

}







function TrendChart({ sessions }) {
  const [aggregation, setAggregation] = useState("weekly");

  const trendData = useMemo(() => {
    if (!sessions || sessions.length === 0) {
      return [];
    }

    const buckets = {};

    sessions.forEach((session) => {
      const riskScore = Number(session.risk_score);

      if (!Number.isFinite(riskScore)) {
        return;
      }

      const rawDate =
        session.updated_at ||
        session.created_at ||
        session.completed_at ||
        "";

      if (!rawDate) {
        return;
      }

      const date = new Date(rawDate);

      if (Number.isNaN(date.getTime())) {
        return;
      }

      let bucketKey;

      if (aggregation === "monthly") {
        bucketKey = `${date.getFullYear()}-${String(
          date.getMonth() + 1
        ).padStart(2, "0")}`;
      } else {
        const startOfYear = new Date(date.getFullYear(), 0, 1);
        const dayOfYear =
          Math.floor(
            (date - startOfYear) / (24 * 60 * 60 * 1000)
          ) + 1;

        const week = Math.ceil(dayOfYear / 7);

        bucketKey = `${date.getFullYear()}-W${String(
          week
        ).padStart(2, "0")}`;
      }

      if (!buckets[bucketKey]) {
        buckets[bucketKey] = {
          period: bucketKey,
          passed: 0,
          total: 0,
        };
      }

      buckets[bucketKey].total += 1;

      if (riskScore < 0.6) {
        buckets[bucketKey].passed += 1;
      }
    });

    return Object.values(buckets)
      .sort((a, b) => a.period.localeCompare(b.period))
      .map((bucket) => ({
        period: bucket.period,
        passRate:
          bucket.total === 0
            ? 0
            : Number(
                ((bucket.passed / bucket.total) * 100).toFixed(2)
              ),
      }));
  }, [sessions, aggregation]);

  return (
    <Card
      title="Pass-rate trend"
      description="Weekly or monthly percentage of sessions that passed."
    >
      <div className="mb-4 flex gap-2">
        <button
          onClick={() => setAggregation("weekly")}
          className={cn(
            "rounded px-3 py-1 text-xs",
            aggregation === "weekly"
              ? "bg-accent/20"
              : "text-muted"
          )}
        >
          Weekly
        </button>

        <button
          onClick={() => setAggregation("monthly")}
          className={cn(
            "rounded px-3 py-1 text-xs",
            aggregation === "monthly"
              ? "bg-accent/20"
              : "text-muted"
          )}
        >
          Monthly
        </button>
      </div>

      {trendData.length === 0 ? (
        <div className="py-8 text-center text-sm text-muted">
          No evaluation data available for pass-rate trend.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />

            <XAxis dataKey="period" />

            <YAxis
              domain={[0, 100]}
              tickFormatter={(value) => `${value}%`}
            />

            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(value) => [`${value}%`, "Pass rate"]}
            />

            <Line
              type="monotone"
              dataKey="passRate"
              name="Pass rate"
              stroke="#6366f1"
              strokeWidth={2}
              dot
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}

function WeakAreaTagCloud({ sessions }) {
  const weakAreas = useMemo(() => {
    const counts = {};

    if (!sessions || sessions.length === 0) {
      return [];
    }

    sessions.forEach((session) => {
      const evaluation =
        session.evaluation_analysis ||
        session.evaluation_result ||
        session.evaluation ||
        {};

      const topics = [];

      const knowledgeGaps =
        evaluation?.technical_accuracy?.knowledge_gaps;

      if (Array.isArray(knowledgeGaps)) {
        topics.push(...knowledgeGaps);
      }

      const improvements =
        evaluation?.feedback?.improvements;

      if (Array.isArray(improvements)) {
        topics.push(...improvements);
      }

      topics.forEach((topic) => {
        const normalized = String(topic).trim();

        if (!normalized) {
          return;
        }

        const key = normalized.toLowerCase();

        if (!counts[key]) {
          counts[key] = {
            topic: normalized,
            count: 0,
          };
        }

        counts[key].count += 1;
      });
    });

    return Object.values(counts).sort(
      (a, b) =>
        b.count - a.count ||
        a.topic.localeCompare(b.topic)
    );
  }, [sessions]);

  const maxCount =
    weakAreas.length > 0
      ? Math.max(...weakAreas.map((item) => item.count))
      : 1;

  return (
    <Card
      title="Weak areas"
      description="Common topics identified from evaluated sessions."
    >
      {weakAreas.length === 0 ? (
        <div className="py-8 text-center text-sm text-muted">
          No weak areas found.
        </div>
      ) : (
        <div className="flex min-h-[220px] flex-wrap items-center justify-center gap-3 p-4">
          {weakAreas.map((item) => {
            const size =
              0.85 +
              (item.count / maxCount) * 0.75;

            return (
              <span
                key={item.topic}
                title={`${item.count} occurrence${
                  item.count === 1 ? "" : "s"
                }`}
                className="rounded-full border border-border bg-bg-card px-3 py-2 text-center"
                style={{
                  fontSize: `${size}rem`,
                }}
              >
                {item.topic}
              </span>
            );
          })}
        </div>
      )}
    </Card>
  );
}







export default function AnalyticsPage(){



// =============================
// Recruiter Dashboard State
// =============================


const [candidates,setCandidates]=useState([]);



const [candidateForm,setCandidateForm]=useState({

 name:"",
 role:"",
 status:"Scheduled",
 score:"",
 risk:""

});





const addCandidate=()=>{

const removeCandidate = (id) => {

  setCandidates((prev) =>
    prev.filter((candidate) => candidate.id !== id)
  );

  toast.success(
    "Candidate removed"
  );

};
 if(
 !candidateForm.name ||
 !candidateForm.role
 ){

 toast.error(
 "Candidate name and role required"
 );

 return;

 }



 setCandidates([

 ...candidates,

 {
  id:Date.now(),
  ...candidateForm
 }

 ]);



 setCandidateForm({

 name:"",
 role:"",
 status:"Scheduled",
 score:"",
 risk:""

 });


 toast.success(
 "Candidate added"
 );


};





const stats=useSWR(
"/session-statistics",
{
 refreshInterval:10000
}
);


const faults=useSWR(
"/fault-statistics",
{
 refreshInterval:10000
}
);


const dlq=useSWR(
"/dead-letter-queue?limit=50",
{
 refreshInterval:10000
}
);


const completed=useSWR(
"/completed-sessions?limit=10000",
{
 refreshInterval:10000
}
);


const failed=useSWR(
"/failed-sessions?limit=10000",
{
 refreshInterval:10000
}
);



const [dateRange,setDateRange]=useState("all");


const [drillDown,setDrillDown]=useState(null);




const allSessions=useMemo(()=>[

...(completed.data?.sessions ?? []),

...(failed.data?.sessions ?? [])

],
[
completed.data,
failed.data
]);




const filteredSessions=useMemo(()=>{

return filterByDate(
allSessions,
dateRange
);

},[
allSessions,
dateRange
]);


  const breakdown = useMemo(()=>{

    if(!stats.data)
      return [];

    return Object.entries(
      stats.data.status_breakdown || {}
    ).map(([status,count])=>({
      status,
      count
    }));

  },[stats.data]);



  const failureData = useMemo(()=>{

    if(!faults.data)
      return [];

    return Object.entries(
      faults.data.fault_statistics?.failures_by_type || {}
    ).map(([type,count])=>({
      type,
      count
    }));

  },[faults.data]);




  const handleExport = useCallback(()=>{

    if (candidates.length > 0) {
      // Export recruiter dashboard candidates
      exportAnalyticsCSV({ 
        candidates, 
        stats: stats.data, 
        faults: faults.data 
      });
      toast.success("Export complete");
    } else if (stats.data) {
      // Export analytics statistics
      exportAnalyticsCSV({ 
        candidates: [], 
        stats: stats.data, 
        faults: faults.data 
      });
      toast.success("Export complete");
    } else {
      toast.error("No data to export");
    }

  },[candidates, stats.data, faults.data]);
  const handlePDFExport = useCallback(async () => {
  if (!candidates.length && !stats.data && !faults.data) {
    toast.error("No data to export");
    return;
  }

  try {
    await exportAnalyticsPDF({
      candidates,
      stats: stats.data,
      faults: faults.data,
    });

    toast.success("PDF export complete");
  } catch (error) {
    console.error("PDF export failed:", error);
    toast.error("Failed to export PDF");
  }
}, [candidates, stats.data, faults.data]);




return (

<div className="space-y-6 animate-fade-in">



{/* ===========================
    RECRUITER DASHBOARD
=========================== */}



<div className="space-y-5">


<div>

<h1 className="text-2xl font-semibold text-zinc-50">
Recruiter Dashboard
</h1>


<p className="text-sm text-muted">
AI powered candidate hiring insights and interview evaluation.
</p>


</div>




<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">


<Stat
label="Total Candidates"
value={candidates.length}
/>


<Stat
label="Scheduled Interviews"
value={
candidates.filter(
c=>c.status==="Scheduled"
).length
}
/>


<Stat
label="Completed Interviews"
value={
candidates.filter(
c=>c.status==="Completed"
).length
}
/>


<Stat
label="Average Score"
value={
candidates.length

?

Math.round(

candidates.reduce(

(sum,c)=>

sum+(Number(c.score)||0)

,0)

/
candidates.length

)+"%"

:

"0%"

}
/>



</div>





<Card
title="Add Candidate"
description="Enter candidate interview details"
>


<div className="grid gap-3">


<input
className="rounded border border-border bg-bg-card p-2"
placeholder="Candidate name"
value={candidateForm.name}

onChange={(e)=>

setCandidateForm({

...candidateForm,

name:e.target.value

})

}
/>



<input
className="rounded border border-border bg-bg-card p-2"
placeholder="Role"

value={candidateForm.role}

onChange={(e)=>

setCandidateForm({

...candidateForm,

role:e.target.value

})

}

/>



<select

className="rounded border border-border bg-bg-card p-2"

value={candidateForm.status}

onChange={(e)=>

setCandidateForm({

...candidateForm,

status:e.target.value

})

}

>


<option>
Scheduled
</option>

<option>
Under Review
</option>

<option>
Completed
</option>


</select>





<input

type="number"

className="rounded border border-border bg-bg-card p-2"

placeholder="Score"

value={candidateForm.score}

onChange={(e)=>

setCandidateForm({

...candidateForm,

score:e.target.value

})

}

/>




<select

className="rounded border border-border bg-bg-card p-2"

value={candidateForm.risk}

onChange={(e)=>

setCandidateForm({

...candidateForm,

risk:e.target.value

})

}

>


<option value="">
Select Risk
</option>

<option>
Low
</option>

<option>
Medium
</option>

<option>
High
</option>


</select>




<button

onClick={addCandidate}

className="rounded bg-accent px-4 py-2 text-white"

>

Add Candidate

</button>



</div>


</Card>







<Card

title="Candidate Evaluation"

description="Recruiter view of candidate interview results."

>


 <div className="overflow-x-auto">
    <table className="w-full min-w-[600px] text-sm">


<thead>

<tr className="text-left text-muted">


<th className="py-3">
Candidate
</th>


<th>
Role
</th>


<th>
Status
</th>


<th>
Score
</th>


<th>
Risk
</th>


</tr>


</thead>




<tbody>



{

candidates.map((c)=>(


<tr
key={c.id}
className="border-t border-border"
>


<td className="py-3">
{c.name}
</td>


<td>
{c.role}
</td>


<td>
{c.status}
</td>


<td>

{
c.score
?

c.score+"%"

:

"-"

}

</td>


<td>

{
c.risk || "-"

}

</td>


</tr>


))


}




{

candidates.length===0 &&

<tr>

<td

colSpan="5"

className="py-6 text-center text-muted"

>

No candidates added yet.

</td>


</tr>


}



</tbody>


</table>
</div>

</Card>


</div>







{/* ===========================
        OLD ANALYTICS
=========================== */}



<div className="flex items-end justify-between">


<div>

<h1 className="text-2xl font-semibold text-zinc-50">
Analytics
</h1>


<p className="text-sm text-muted">
Risk distribution, failure modes, trends, and export.
</p>


</div>



<button

onClick={handleExport}

className="flex items-center gap-2 rounded border border-border bg-bg-card px-3 py-2 text-xs"

>

<Download size={14}/>

Export CSV

</button>

<button
  onClick={handlePDFExport}
  className="flex items-center gap-2 rounded border border-border bg-bg-card px-3 py-2 text-xs"
>
  <Download size={14} />
  Export PDF
</button>

</div>





<div className="flex flex-wrap gap-2">


<Calendar size={14}/>


{
DATE_PRESETS.map(p=>(


<button

key={p.value}

onClick={()=>setDateRange(p.value)}

className={cn(

"rounded px-3 py-1 text-xs",

dateRange===p.value

?

"bg-accent/20"

:

"text-muted"

)}

>

{p.label}

</button>


))

}


</div>







<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">


<Stat

label="Total sessions"

value={
stats.data?.total_sessions ?? 0
}

/>


<Stat

label="Avg risk"

value={

stats.data

?

stats.data.risk_score_stats
?.average_risk_score
?.toFixed(3)

:

0

}

/>



<Stat

label="High risk"

value={

stats.data?.risk_score_stats
?.high_risk_sessions ?? 0

}

/>



<Stat

label="DLQ size"

value={
dlq.data?.count ?? 0
}

/>



</div>






<div className="grid grid-cols-1 gap-4 lg:grid-cols-2">


<Card
title="Sessions by status"
description="Distribution across lifecycle states."
>


{

stats.error ?

<ErrorState
error={stats.error}
onRetry={()=>stats.mutate()}
/>


:


<ResponsiveContainer
width="100%"
height={280}
>


<BarChart data={breakdown}>


<CartesianGrid strokeDasharray="3 3"/>

<XAxis dataKey="status"/>

<YAxis/>

<Tooltip {...TOOLTIP_STYLE}/>


<Bar

dataKey="count"

fill="#6366f1"

/>


</BarChart>


</ResponsiveContainer>


}



</Card>






<Card

title="Failure breakdown"

description="Counts grouped by failure type."

>


<ResponsiveContainer

width="100%"

height={280}

>


<BarChart data={failureData}>


<CartesianGrid strokeDasharray="3 3"/>

<XAxis dataKey="type"/>

<YAxis/>

<Tooltip {...TOOLTIP_STYLE}/>


<Bar

dataKey="count"

fill="#ef4444"

/>


</BarChart>


</ResponsiveContainer>


</Card>



</div>






<div className="grid grid-cols-1 gap-4 lg:grid-cols-2">


<RiskDistribution

sessions={filteredSessions}

loading={
completed.isLoading &&
failed.isLoading
}

onDrillDown={
(type)=>setDrillDown(type)
}

/>



<TrendChart

sessions={filteredSessions}

/>


</div>




</div>

);

}