import { useState, useEffect, useCallback } from "react";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

// ─── Apple-inspired design tokens ─────────────────────────────
const T = {
  bg:           "#FFFFFF",
  surface:      "#F5F5F7",
  card:         "#FFFFFF",
  border:       "#E5E5EA",
  borderLight:  "#F2F2F7",
  accent:       "#0071E3",
  accentLight:  "#EBF3FD",
  green:        "#34C759",
  greenLight:   "#EDFAF1",
  amber:        "#FF9F0A",
  amberLight:   "#FFF5E6",
  red:          "#FF3B30",
  redLight:     "#FFECEB",
  orange:       "#FF6B35",
  orangeLight:  "#FFF1EB",
  purple:       "#BF5AF2",
  purpleLight:  "#F7EFFE",
  text:         "#1D1D1F",
  secondary:    "#6E6E73",
  tertiary:     "#AEAEB2",
  shadow:       "0 2px 12px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04)",
  shadowMd:     "0 4px 24px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06)",
  shadowLg:     "0 20px 60px rgba(0,0,0,0.14), 0 4px 16px rgba(0,0,0,0.08)",
};

// ─── Status config ─────────────────────────────────────────────
const STATUS = {
  submitted:        { c:"#6E6E73", bg:"#F5F5F7", label:"Submitted" },
  validating:       { c:"#0071E3", bg:"#EBF3FD", label:"Validating", pulse:true },
  auto_approved:    { c:"#1A8A3A", bg:"#EDFAF1", label:"Auto Approved" },
  pending_approval: { c:"#C47700", bg:"#FFF5E6", label:"Pending",    pulse:true },
  approved:         { c:"#1A8A3A", bg:"#EDFAF1", label:"Approved" },
  rejected:         { c:"#CC2020", bg:"#FFECEB", label:"Rejected" },
  executing:        { c:"#0071E3", bg:"#EBF3FD", label:"Executing",  pulse:true },
  completed:        { c:"#1A8A3A", bg:"#EDFAF1", label:"Completed" },
  failed:           { c:"#CC2020", bg:"#FFECEB", label:"Failed" },
  rolled_back:      { c:"#CC5500", bg:"#FFF1EB", label:"Rolled Back" },
};

const IMPACT = {
  low:      { c:"#34C759", bg:"#EDFAF1", label:"Low",      w:"25%" },
  medium:   { c:"#FF9F0A", bg:"#FFF5E6", label:"Medium",   w:"50%" },
  high:     { c:"#FF6B35", bg:"#FFF1EB", label:"High",     w:"75%" },
  critical: { c:"#FF3B30", bg:"#FFECEB", label:"Critical", w:"100%" },
};

const EVENT_META = {
  decision_submitted:          { c:"#AEAEB2", sym:"→", label:"Submitted" },
  freshness_check_started:     { c:"#0071E3", sym:"⟳", label:"Freshness Check" },
  freshness_check_passed:      { c:"#34C759", sym:"✓", label:"Data Fresh" },
  freshness_check_failed:      { c:"#FF3B30", sym:"✗", label:"Stale Data Detected" },
  ai_classification_completed: { c:"#BF5AF2", sym:"◈", label:"AI Classified" },
  low_confidence_escalation:   { c:"#FF9F0A", sym:"⚠", label:"Low Confidence — Escalated" },
  rules_engine_applied:        { c:"#FF6B35", sym:"⚡", label:"Rules Overrode AI" },
  rules_engine_no_match:       { c:"#AEAEB2", sym:"—", label:"No Rules Matched" },
  counterfactual_recorded:     { c:"#BF5AF2", sym:"⟷", label:"Counterfactual Logged" },
  classification_finalized:    { c:"#0071E3", sym:"◉", label:"Classification Final" },
  decision_approved:           { c:"#34C759", sym:"✓", label:"Approved" },
  partial_approval_recorded:   { c:"#FF9F0A", sym:"½", label:"Partial Approval" },
  decision_rejected:           { c:"#FF3B30", sym:"✗", label:"Rejected" },
  approval_expired:            { c:"#FF6B35", sym:"⏱", label:"Approval Expired" },
  agent_suspended_block:       { c:"#FF3B30", sym:"⛔", label:"Agent Blocked" },
  probationary_override:       { c:"#FF9F0A", sym:"⚠", label:"Probationary Override" },
  execution_started:           { c:"#0071E3", sym:"▶", label:"Executing" },
  snapshot_captured:           { c:"#BF5AF2", sym:"◎", label:"Snapshot Captured" },
  execution_completed:         { c:"#34C759", sym:"✓", label:"Executed" },
  execution_failed:            { c:"#FF3B30", sym:"✗", label:"Execution Failed" },
  rollback_started:            { c:"#FF6B35", sym:"↩", label:"Rollback Started" },
  rollback_completed:          { c:"#34C759", sym:"↩", label:"Rolled Back" },
  pipeline_error:              { c:"#FF3B30", sym:"!", label:"Pipeline Error" },
};

const ACTION_LABEL = a => ({
  wire_transfer:"Wire Transfer", bank_transfer:"Bank Transfer",
  payment:"Payment", send_email:"Send Email",
  send_reminder_email:"Send Reminder", modify_document:"Modify Document",
  update_policy:"Update Policy", update_payment_status:"Update Payment Status",
  generate_report:"Generate Report", delete_record:"Delete Record",
  delete_data:"Delete Data", purge:"Purge Data",
}[a] || a?.replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase()) || "—");

const fmt = {
  id:    s => s ? s.substring(0,8).toUpperCase() : "—",
  agent: s => s?.replace(/-v\d+$/,"").replace(/-/g," ").replace(/\b\w/g,c=>c.toUpperCase()) || s || "—",
  time:  s => {
    if (!s) return "—";
    const diff = Math.floor((Date.now()-new Date(s))/1000);
    if (diff < 60)    return `${diff}s ago`;
    if (diff < 3600)  return `${Math.floor(diff/60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
    return new Date(s).toLocaleDateString();
  },
  clock: s => s ? new Date(s).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit"}) : "—",
};

// ─── API hook ─────────────────────────────────────────────────
function useApi(cfg) {
  return useCallback(async (path, opts={}) => {
    const key = opts.role==="admin"    ? cfg.adminKey
              : opts.role==="approver" ? cfg.approverKey
              : cfg.agentKey;
    const res = await fetch(`${cfg.url}${path}`, {
      method: opts.method || "GET",
      headers: { "X-API-Key":key||"", "Content-Type":"application/json" },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return res.json();
  }, [cfg]);
}

// ─── Global styles ─────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#F5F5F7; font-family:-apple-system,BlinkMacSystemFont,'Inter','SF Pro Text',Helvetica,Arial,sans-serif; }
  ::-webkit-scrollbar { width:5px; }
  ::-webkit-scrollbar-track { background:transparent; }
  ::-webkit-scrollbar-thumb { background:#D2D2D7; border-radius:10px; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.35} }
  @keyframes spin   { to{transform:rotate(360deg)} }
  @keyframes slideIn{ from{transform:translateX(24px);opacity:0} to{transform:translateX(0);opacity:1} }
  @keyframes fadeIn { from{opacity:0} to{opacity:1} }
  input::placeholder,textarea::placeholder { color:#AEAEB2; }
  button { font-family:inherit; }
  input,select,textarea { font-family:inherit; }
  a { text-decoration:none; }
`;

// ─── Atoms ─────────────────────────────────────────────────────
const Spin = () => (
  <div style={{width:16,height:16,border:"2px solid #E5E5EA",
    borderTopColor:T.accent,borderRadius:"50%",animation:"spin 0.75s linear infinite"}}/>
);

const Empty = ({msg}) => (
  <div style={{textAlign:"center",padding:"48px 0",color:T.tertiary}}>
    <div style={{fontSize:32,marginBottom:10,opacity:0.4}}>○</div>
    <div style={{fontSize:13,color:T.secondary}}>{msg}</div>
  </div>
);

const Badge = ({status}) => {
  const s = STATUS[status] || {c:"#6E6E73",bg:"#F5F5F7",label:status};
  return (
    <span style={{background:s.bg,color:s.c,
      padding:"3px 10px",borderRadius:20,fontSize:11,fontWeight:600,
      display:"inline-flex",alignItems:"center",gap:5,whiteSpace:"nowrap",
      letterSpacing:"0.01em"}}>
      {s.pulse && <span style={{width:5,height:5,borderRadius:"50%",
        background:s.c,animation:"pulse 1.5s infinite",display:"inline-block"}}/>}
      {s.label}
    </span>
  );
};

const ImpactBadge = ({impact}) => {
  const i = IMPACT[impact] || {c:T.secondary,bg:T.surface,label:impact||"—"};
  return (
    <span style={{background:i.bg,color:i.c,
      padding:"3px 10px",borderRadius:20,fontSize:11,fontWeight:600}}>
      {i.label}
    </span>
  );
};

const ImpactBar = ({impact}) => {
  const i = IMPACT[impact] || {c:T.tertiary,label:impact||"—",w:"0%"};
  return (
    <div style={{display:"flex",alignItems:"center",gap:8}}>
      <div style={{width:56,height:3,background:"#E5E5EA",borderRadius:2,overflow:"hidden"}}>
        <div style={{width:i.w,height:"100%",background:i.c,borderRadius:2,
          transition:"width 0.5s ease"}}/>
      </div>
      <span style={{color:i.c,fontSize:11,fontWeight:600}}>{i.label}</span>
    </div>
  );
};

const Pill = ({onClick,color,bg,label}) => (
  <button onClick={onClick} style={{
    background:bg,color,border:"none",
    padding:"8px 16px",borderRadius:8,fontSize:13,fontWeight:500,
    cursor:"pointer",transition:"all 0.15s",whiteSpace:"nowrap",
    boxShadow:T.shadow}}>
    {label}
  </button>
);

const StatCard = ({label,value,sub,color,icon,accent}) => (
  <div style={{background:T.card,borderRadius:16,padding:"22px 24px",
    boxShadow:T.shadow,position:"relative",overflow:"hidden"}}>
    <div style={{position:"absolute",top:-8,right:-8,width:72,height:72,
      borderRadius:"50%",background:`${accent||color||T.accent}08`}}/>
    <div style={{fontSize:11,color:T.secondary,marginBottom:10,
      fontWeight:500,letterSpacing:"0.02em",textTransform:"uppercase"}}>{label}</div>
    <div style={{fontSize:32,fontWeight:700,color:color||T.text,
      lineHeight:1,letterSpacing:"-0.02em"}}>{value??0}</div>
    {sub && <div style={{fontSize:12,color:T.secondary,marginTop:6}}>{sub}</div>}
  </div>
);

const Divider = () => (
  <div style={{height:1,background:T.border,margin:"0"}}/>
);

// ─── Audit Timeline ─────────────────────────────────────────────
const AuditTimeline = ({events}) => (
  <div>
    {events.map((e,i) => {
      const m = EVENT_META[e.event_type] || {c:T.tertiary,sym:"·",label:e.event_type};
      return (
        <div key={e.id||i} style={{display:"flex",gap:12,position:"relative"}}>
          {i < events.length-1 && (
            <div style={{position:"absolute",left:15,top:30,width:1,
              height:"calc(100% + 4px)",background:T.border}}/>
          )}
          <div style={{width:30,height:30,borderRadius:"50%",flexShrink:0,
            background:`${m.c}15`,border:`1.5px solid ${m.c}40`,
            display:"flex",alignItems:"center",justifyContent:"center",
            fontSize:11,color:m.c,marginTop:2,zIndex:1,fontWeight:600}}>
            {m.sym}
          </div>
          <div style={{flex:1,paddingBottom:16}}>
            <div style={{display:"flex",justifyContent:"space-between",
              alignItems:"flex-start",gap:8}}>
              <div style={{fontSize:13,fontWeight:500,color:T.text}}>{m.label}</div>
              <div style={{fontSize:11,color:T.tertiary,whiteSpace:"nowrap",
                fontVariantNumeric:"tabular-nums"}}>{fmt.clock(e.timestamp)}</div>
            </div>
            <div style={{fontSize:11,color:T.secondary,marginTop:1}}>{e.actor}</div>
            {e.details && Object.keys(e.details).length > 0 && (
              <div style={{marginTop:8,padding:"10px 12px",background:T.surface,
                borderRadius:8,border:`1px solid ${T.border}`}}>
                {Object.entries(e.details).slice(0,6).map(([k,v])=>(
                  <div key={k} style={{display:"flex",gap:10,fontSize:11,marginBottom:3}}>
                    <span style={{color:T.secondary,minWidth:110,flexShrink:0,
                      fontVariantNumeric:"tabular-nums"}}>{k}</span>
                    <span style={{color:T.text,wordBreak:"break-all"}}>
                      {typeof v==="object"?JSON.stringify(v).slice(0,100):String(v).slice(0,100)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      );
    })}
  </div>
);

// ─── Detail Panel ───────────────────────────────────────────────
const DetailPanel = ({d,audit,loading,onClose,onAction}) => {
  const [approver,setApprover] = useState("");
  const [reason,setReason]     = useState("");
  const [mode,setMode]         = useState(null);
  const [acting,setActing]     = useState(false);
  const [err,setErr]           = useState("");

  const doAction = async () => {
    setErr(""); setActing(true);
    try { await onAction(mode,{approver_id:approver,reason,requested_by:approver}); setMode(null); }
    catch(e){ setErr(e.message); }
    setActing(false);
  };

  if (!d) return null;
  const clf = d.classification;

  const inputStyle = {
    width:"100%",background:T.surface,border:`1px solid ${T.border}`,
    borderRadius:8,padding:"9px 12px",color:T.text,fontSize:13,
    outline:"none",transition:"border-color 0.15s",
  };

  return (
    <div style={{position:"fixed",right:0,top:0,bottom:0,width:520,
      background:T.bg,borderLeft:`1px solid ${T.border}`,
      display:"flex",flexDirection:"column",zIndex:100,
      boxShadow:T.shadowLg,animation:"slideIn 0.22s ease"}}>

      {/* Header */}
      <div style={{padding:"20px 24px",borderBottom:`1px solid ${T.border}`,
        display:"flex",justifyContent:"space-between",alignItems:"center",flexShrink:0}}>
        <div>
          <div style={{fontSize:11,color:T.secondary,marginBottom:4,
            textTransform:"uppercase",letterSpacing:"0.06em",fontWeight:500}}>
            Decision Detail
          </div>
          <div style={{fontSize:13,color:T.text,fontWeight:500,
            fontVariantNumeric:"tabular-nums"}}>
            {fmt.id(d.decision_id)}
            <span style={{color:T.tertiary,marginLeft:10,fontSize:12,fontWeight:400}}>
              {fmt.time(d.submitted_at)}
            </span>
          </div>
        </div>
        <button onClick={onClose}
          style={{background:T.surface,border:`1px solid ${T.border}`,color:T.secondary,
            width:32,height:32,borderRadius:8,cursor:"pointer",fontSize:16,
            display:"flex",alignItems:"center",justifyContent:"center",
            transition:"all 0.15s"}}>×</button>
      </div>

      <div style={{flex:1,overflowY:"auto",padding:"0 24px 32px"}}>

        {/* Status + Impact */}
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginTop:20}}>
          <div style={{background:T.surface,borderRadius:12,padding:"14px 16px"}}>
            <div style={{fontSize:10,color:T.secondary,marginBottom:8,
              textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:500}}>Status</div>
            <Badge status={d.status}/>
          </div>
          <div style={{background:T.surface,borderRadius:12,padding:"14px 16px"}}>
            <div style={{fontSize:10,color:T.secondary,marginBottom:8,
              textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:500}}>Impact</div>
            {clf?.impact ? <ImpactBar impact={clf.impact}/>
              : <span style={{color:T.tertiary,fontSize:12}}>Classifying…</span>}
          </div>
        </div>

        {/* Info table */}
        <div style={{marginTop:14,background:T.surface,borderRadius:12,overflow:"hidden"}}>
          {[
            ["Action",      ACTION_LABEL(d.action_type), T.text],
            ["Agent",       fmt.agent(d.agent_id), T.text],
            ["Description", d.description, T.text],
            ["Route",       clf?.route?.replace(/_/g," "), T.accent],
            ["Confidence",  clf?.confidence!=null?`${(clf.confidence*100).toFixed(0)}%`:null, T.text],
            ["Approvers",   clf?.suggested_approvers?.join(", "), T.text],
            ["Expires",     d.expires_at?fmt.time(d.expires_at):null, T.text],
          ].map(([k,v,color],i,arr)=>(
            <div key={k} style={{display:"flex",gap:12,padding:"10px 16px",
              borderBottom:i<arr.length-1?`1px solid ${T.border}`:"none"}}>
              <span style={{color:T.secondary,fontSize:12,width:88,flexShrink:0,paddingTop:1}}>
                {k}
              </span>
              <span style={{color:color||T.text,fontSize:13,wordBreak:"break-word",
                fontWeight:k==="Route"?500:400}}>{v||"—"}</span>
            </div>
          ))}
        </div>

        {/* Risk reason */}
        {clf?.risk_reason && (
          <div style={{marginTop:12,padding:"14px 16px",
            background:T.amberLight,borderRadius:12,
            borderLeft:`3px solid ${T.amber}`}}>
            <div style={{fontSize:10,color:T.amber,marginBottom:6,
              textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:600}}>Risk Reason</div>
            <div style={{fontSize:13,color:T.text,lineHeight:1.65}}>{clf.risk_reason}</div>
          </div>
        )}

        {/* Counterfactual */}
        {d.counterfactual && (
          <div style={{marginTop:12,padding:"14px 16px",
            background:T.purpleLight,borderRadius:12,
            borderLeft:`3px solid ${T.purple}`}}>
            <div style={{fontSize:10,color:T.purple,marginBottom:12,
              textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:600}}>
              Counterfactual
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:10}}>
              {["without_rules_engine","with_rules_engine"].map(k=>(
                <div key={k} style={{background:"rgba(255,255,255,0.7)",
                  borderRadius:8,padding:"10px 12px"}}>
                  <div style={{fontSize:10,color:T.secondary,marginBottom:5}}>
                    {k==="without_rules_engine"?"Without Rules":"With Rules"}
                  </div>
                  <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:2}}>
                    {d.counterfactual[k]?.route?.replace(/_/g," ")||"—"}
                  </div>
                  <div style={{fontSize:11,color:T.secondary}}>
                    {d.counterfactual[k]?.impact}
                  </div>
                </div>
              ))}
            </div>
            <div style={{fontSize:12,color:T.text,lineHeight:1.6}}>
              {d.counterfactual.summary}
            </div>
          </div>
        )}

        {/* Payload */}
        {d.payload && Object.keys(d.payload).length > 0 && (
          <div style={{marginTop:12}}>
            <div style={{fontSize:10,color:T.secondary,marginBottom:8,
              textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:500}}>Payload</div>
            <div style={{background:T.surface,borderRadius:12,
              padding:"12px 16px",fontSize:12,color:T.text,lineHeight:1.8}}>
              {Object.entries(d.payload).map(([k,v])=>(
                <div key={k} style={{display:"flex",gap:10}}>
                  <span style={{color:T.secondary,minWidth:100}}>{k}</span>
                  <span style={{color:T.accent,fontWeight:500}}>{JSON.stringify(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        {["pending_approval","approved","auto_approved","completed"].includes(d.status) && (
          <div style={{marginTop:20}}>
            <div style={{fontSize:10,color:T.secondary,marginBottom:12,
              textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:500}}>Actions</div>

            {err && (
              <div style={{marginBottom:10,padding:"8px 12px",background:T.redLight,
                borderRadius:8,fontSize:12,color:T.red}}>{err}</div>
            )}

            {mode && (
              <div style={{marginBottom:12,display:"flex",flexDirection:"column",gap:8}}>
                <input value={approver} onChange={e=>setApprover(e.target.value)}
                  placeholder="Your name or email"
                  style={inputStyle}/>
                {(mode==="reject"||mode==="rollback") && (
                  <input value={reason} onChange={e=>setReason(e.target.value)}
                    placeholder={mode==="reject"?"Rejection reason (required)":"Rollback reason"}
                    style={inputStyle}/>
                )}
                <div style={{display:"flex",gap:8}}>
                  <button onClick={doAction}
                    style={{flex:1,padding:"10px",borderRadius:8,border:"none",
                      fontWeight:600,fontSize:13,cursor:"pointer",
                      background:mode==="reject"?T.red:T.accent,
                      color:"white",transition:"opacity 0.15s",
                      opacity:acting?0.6:1}}>
                    {acting?"Processing…":`Confirm ${mode.charAt(0).toUpperCase()+mode.slice(1)}`}
                  </button>
                  <button onClick={()=>{setMode(null);setErr("");}}
                    style={{padding:"10px 16px",borderRadius:8,
                      border:`1px solid ${T.border}`,background:T.surface,
                      color:T.secondary,fontSize:13,cursor:"pointer",fontWeight:500}}>
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {!mode && (
              <div style={{display:"flex",flexWrap:"wrap",gap:8}}>
                {d.status==="pending_approval" && <>
                  <button onClick={()=>setMode("approve")}
                    style={{padding:"9px 18px",borderRadius:8,border:"none",
                      background:T.green,color:"white",fontSize:13,fontWeight:600,
                      cursor:"pointer",boxShadow:T.shadow}}>
                    ✓ Approve
                  </button>
                  <button onClick={()=>setMode("reject")}
                    style={{padding:"9px 18px",borderRadius:8,
                      border:`1px solid ${T.border}`,background:T.bg,
                      color:T.red,fontSize:13,fontWeight:600,cursor:"pointer"}}>
                    ✗ Reject
                  </button>
                </>}
                {(d.status==="approved"||d.status==="auto_approved") && (
                  <button onClick={()=>setMode("execute")}
                    style={{padding:"9px 18px",borderRadius:8,border:"none",
                      background:T.accent,color:"white",fontSize:13,fontWeight:600,
                      cursor:"pointer",boxShadow:T.shadow}}>
                    ▶ Execute
                  </button>
                )}
                {d.status==="completed" && d.rollback_available && (
                  <button onClick={()=>setMode("rollback")}
                    style={{padding:"9px 18px",borderRadius:8,
                      border:`1px solid ${T.border}`,background:T.bg,
                      color:T.orange,fontSize:13,fontWeight:600,cursor:"pointer"}}>
                    ↩ Rollback
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Audit trail */}
        <div style={{marginTop:24}}>
          <div style={{fontSize:10,color:T.secondary,marginBottom:16,
            textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:500}}>
            Pipeline Trail · {audit.length} events
          </div>
          {loading
            ? <div style={{display:"flex",justifyContent:"center",padding:30}}><Spin/></div>
            : audit.length ? <AuditTimeline events={audit}/>
            : <Empty msg="No events yet"/>}
        </div>
      </div>
    </div>
  );
};

// ─── Decision Row ────────────────────────────────────────────────
const COLS = "80px 1fr 130px 100px 120px 72px";
const HEADERS = ["ID","Action","Agent","Impact","Status","Time"];

const TableHead = () => (
  <div style={{display:"grid",gridTemplateColumns:COLS,gap:16,
    padding:"10px 20px",borderBottom:`1px solid ${T.border}`}}>
    {HEADERS.map(h=>(
      <div key={h} style={{fontSize:11,color:T.secondary,fontWeight:500,
        letterSpacing:"0.02em"}}>{h}</div>
    ))}
  </div>
);

const DecisionRow = ({d,onClick,selected}) => (
  <div onClick={onClick}
    style={{display:"grid",gridTemplateColumns:COLS,alignItems:"center",
      gap:16,padding:"13px 20px",cursor:"pointer",
      background:selected?T.accentLight:"transparent",
      borderLeft:selected?`3px solid ${T.accent}`:"3px solid transparent",
      borderBottom:`1px solid ${T.borderLight}`,
      transition:"all 0.12s"}}>
    <span style={{fontSize:12,color:T.accent,fontWeight:500,
      fontVariantNumeric:"tabular-nums",letterSpacing:"0.02em"}}>
      {fmt.id(d.decision_id)}
    </span>
    <div>
      <div style={{color:T.text,fontSize:13,fontWeight:500,marginBottom:2}}>
        {ACTION_LABEL(d.action_type)}
      </div>
      <div style={{color:T.secondary,fontSize:12,overflow:"hidden",
        textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:280}}>
        {d.description}
      </div>
    </div>
    <div style={{color:T.secondary,fontSize:12}}>{fmt.agent(d.agent_id)}</div>
    <div>{d.classification?.impact
      ? <ImpactBadge impact={d.classification.impact}/>
      : <span style={{color:T.tertiary,fontSize:11}}>—</span>}</div>
    <Badge status={d.status}/>
    <div style={{color:T.tertiary,fontSize:11,textAlign:"right",
      fontVariantNumeric:"tabular-nums"}}>{fmt.time(d.submitted_at)}</div>
  </div>
);

// ─── Pages ────────────────────────────────────────────────────
function OverviewPage({api,onSelectDecision}) {
  const [stats,setStats]     = useState(null);
  const [recent,setRecent]   = useState([]);
  const [healthy,setHealthy] = useState(null);
  const [loading,setLoading] = useState(true);

  const load = useCallback(async()=>{
    try {
      const [s,d,h] = await Promise.all([
        api("/decisions/stats/summary",{role:"admin"}),
        api("/decisions/",{role:"approver"}),
        api("/health",{role:"agent"}),
      ]);
      setStats(s); setRecent(d.decisions?.slice(0,10)||[]); setHealthy(!!h.status);
    } catch(e){ console.error(e); setHealthy(false); }
    finally{ setLoading(false); }
  },[api]);

  useEffect(()=>{load();const t=setInterval(load,15000);return()=>clearInterval(t);},[load]);

  const pending   = stats?.pending_approval||0;
  const completed = stats?.completed||0;
  const rejected  = (stats?.rejected||0)+(stats?.failed||0);
  const total     = stats ? Object.values(stats).reduce((a,b)=>a+b,0) : 0;

  return (
    <div style={{animation:"fadeIn 0.2s ease"}}>
      {/* System status */}
      <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:24,
        padding:"10px 16px",background:T.card,borderRadius:10,
        boxShadow:T.shadow,display:"inline-flex"}}>
        {healthy===null ? <Spin/> : (
          <div style={{width:7,height:7,borderRadius:"50%",
            background:healthy?T.green:T.red,flexShrink:0}}/>
        )}
        <span style={{fontSize:12,color:T.secondary,fontWeight:400}}>
          {healthy===null?"Checking…":healthy?"System operational":"Cannot reach API"}
        </span>
        <span style={{color:T.border}}>·</span>
        <span style={{fontSize:11,color:T.tertiary}}>Auto-refreshes every 15s</span>
      </div>

      {/* Stats */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:14,marginBottom:24}}>
        <StatCard label="Awaiting Approval" value={pending} icon="⏳"
          color={pending>0?T.amber:T.green} accent={T.amber}
          sub={pending>0?"Needs your review":"All clear"}/>
        <StatCard label="Total Decisions"   value={total}     color={T.accent} accent={T.accent}/>
        <StatCard label="Completed"         value={completed} color={T.green}  accent={T.green}/>
        <StatCard label="Rejected"          value={rejected}  color={T.red}    accent={T.red}/>
      </div>

      {/* Recent decisions table */}
      <div style={{background:T.card,borderRadius:16,boxShadow:T.shadow,overflow:"hidden"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",
          padding:"16px 20px"}}>
          <div style={{fontSize:15,fontWeight:600,color:T.text}}>Recent Decisions</div>
          <button onClick={load}
            style={{background:"none",border:"none",color:T.secondary,cursor:"pointer",
              fontSize:13,display:"flex",alignItems:"center",gap:5,fontWeight:500}}>
            ↻ Refresh
          </button>
        </div>
        <Divider/>
        <TableHead/>
        {loading
          ? <div style={{display:"flex",justifyContent:"center",padding:48}}><Spin/></div>
          : recent.length
            ? recent.map(d=><DecisionRow key={d.decision_id} d={d}
                onClick={()=>onSelectDecision(d.decision_id)}/>)
            : <Empty msg="No decisions yet — submit one via the API"/>
        }
      </div>
    </div>
  );
}

function DecisionsPage({api,initialId}) {
  const [all,setAll]           = useState([]);
  const [loading,setLoading]   = useState(true);
  const [search,setSearch]     = useState("");
  const [statusF,setStatusF]   = useState("all");
  const [selected,setSelected] = useState(initialId||null);
  const [detail,setDetail]     = useState(null);
  const [audit,setAudit]       = useState([]);
  const [dLoad,setDLoad]       = useState(false);

  const load = useCallback(async()=>{
    try{ const d=await api("/decisions/",{role:"approver"}); setAll(d.decisions||[]); }
    catch(e){ console.error(e); }
    finally{ setLoading(false); }
  },[api]);

  useEffect(()=>{ load(); },[load]);

  const select = useCallback(async id=>{
    setSelected(id); setDLoad(true);
    try{
      const [d,a] = await Promise.all([
        api(`/decisions/${id}`,{role:"agent"}),
        api(`/decisions/${id}/audit`,{role:"agent"}),
      ]);
      setDetail(d); setAudit(a.events||[]);
    } catch(e){ console.error(e); }
    setDLoad(false);
  },[api]);

  useEffect(()=>{ if(initialId) select(initialId); },[initialId]);

  const doAction = useCallback(async(type,body)=>{
    const rM = {approve:"approver",reject:"approver",execute:"approver",rollback:"admin"};
    const bM = {
      approve:{approver_id:body.approver_id,reason:body.reason},
      reject: {approver_id:body.approver_id,reason:body.reason},
      execute:{requested_by:body.requested_by},
      rollback:{requested_by:body.requested_by,reason:body.reason},
    };
    await api(`/decisions/${selected}/${type}`,{method:"POST",role:rM[type],body:bM[type]});
    await select(selected); await load();
  },[selected,api,select,load]);

  const filtered = all.filter(d=>{
    if(statusF!=="all"&&d.status!==statusF) return false;
    if(search&&![d.agent_id,d.action_type,d.description,d.decision_id]
      .some(v=>v?.toLowerCase().includes(search.toLowerCase()))) return false;
    return true;
  });

  const inputStyle = {
    background:T.surface,border:`1px solid ${T.border}`,borderRadius:8,
    padding:"8px 14px",color:T.text,fontSize:13,outline:"none",fontFamily:"inherit",
  };

  return (
    <div style={{display:"flex",gap:0,position:"relative",animation:"fadeIn 0.2s ease"}}>
      <div style={{flex:1,minWidth:0}}>
        {/* Toolbar */}
        <div style={{display:"flex",gap:8,marginBottom:16,alignItems:"center"}}>
          <input value={search} onChange={e=>setSearch(e.target.value)}
            placeholder="Search by agent, action, description, or ID…"
            style={{...inputStyle,flex:1}}/>
          <select value={statusF} onChange={e=>setStatusF(e.target.value)}
            style={{...inputStyle,cursor:"pointer"}}>
            <option value="all">All Statuses</option>
            {Object.entries(STATUS).map(([k,v])=>(
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
          <button onClick={load}
            style={{...inputStyle,cursor:"pointer",border:`1px solid ${T.border}`,
              color:T.secondary}}>↻</button>
          <span style={{fontSize:12,color:T.secondary,whiteSpace:"nowrap"}}>
            {filtered.length} / {all.length}
          </span>
        </div>

        {/* Table */}
        <div style={{background:T.card,borderRadius:16,
          boxShadow:T.shadow,overflow:"hidden"}}>
          <TableHead/>
          {loading
            ? <div style={{display:"flex",justifyContent:"center",padding:48}}><Spin/></div>
            : filtered.length
              ? filtered.map(d=><DecisionRow key={d.decision_id} d={d}
                  selected={d.decision_id===selected}
                  onClick={()=>select(d.decision_id)}/>)
              : <Empty msg="No decisions match your filters"/>}
        </div>
      </div>

      {selected && (
        <DetailPanel d={detail} audit={audit} loading={dLoad}
          onClose={()=>{setSelected(null);setDetail(null);setAudit([]);}}
          onAction={doAction}/>
      )}
    </div>
  );
}

function RulesPage({api}) {
  const [rules,setRules]       = useState([]);
  const [loading,setLoading]   = useState(true);
  const [toggling,setToggling] = useState(null);

  const load = useCallback(async()=>{
    try{ const d=await api("/rules/",{role:"admin"}); setRules(d.rules||[]); }
    catch(e){ console.error(e); }
    finally{ setLoading(false); }
  },[api]);

  useEffect(()=>{ load(); },[load]);

  const toggle = async r=>{
    setToggling(r.rule_id);
    try{
      await api(`/rules/${r.rule_id}/${r.enabled?"disable":"enable"}`,
        {method:"PATCH",role:"admin"});
      setRules(p=>p.map(x=>x.rule_id===r.rule_id?{...x,enabled:!x.enabled}:x));
    } catch(e){ console.error(e); }
    setToggling(null);
  };

  if (loading) return <div style={{display:"flex",justifyContent:"center",padding:80}}><Spin/></div>;
  const active = rules.filter(r=>r.enabled).length;

  return (
    <div style={{animation:"fadeIn 0.2s ease"}}>
      <div style={{display:"flex",justifyContent:"space-between",
        alignItems:"center",marginBottom:24}}>
        <div>
          <h2 style={{fontSize:22,fontWeight:700,color:T.text,
            letterSpacing:"-0.02em",marginBottom:4}}>Business Rules</h2>
          <p style={{fontSize:13,color:T.secondary}}>
            {active} of {rules.length} rules active · loaded dynamically from Cosmos DB
          </p>
        </div>
        <button onClick={load}
          style={{background:T.surface,border:`1px solid ${T.border}`,color:T.secondary,
            padding:"8px 14px",borderRadius:8,cursor:"pointer",fontSize:13,fontWeight:500}}>
          ↻ Refresh
        </button>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
        {rules.map(r=>(
          <div key={r.rule_id}
            style={{background:T.card,borderRadius:14,padding:"18px 20px",
              boxShadow:T.shadow,opacity:r.enabled?1:0.55,transition:"all 0.2s"}}>
            <div style={{display:"flex",justifyContent:"space-between",
              alignItems:"flex-start",marginBottom:14}}>
              <div style={{flex:1,marginRight:14}}>
                <div style={{fontSize:14,fontWeight:600,color:T.text,marginBottom:4,
                  letterSpacing:"-0.01em"}}>
                  {r.name?.replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase())}
                </div>
                <div style={{fontSize:12,color:T.secondary,lineHeight:1.55}}>{r.description}</div>
              </div>
              {/* Toggle */}
              <div onClick={()=>toggle(r)}
                style={{width:42,height:24,borderRadius:12,cursor:"pointer",flexShrink:0,
                  background:r.enabled?T.green:"#E5E5EA",position:"relative",
                  transition:"background 0.2s"}}>
                {toggling===r.rule_id
                  ? <div style={{position:"absolute",top:"50%",left:"50%",
                      transform:"translate(-50%,-50%)",scale:"0.65"}}><Spin/></div>
                  : <div style={{position:"absolute",top:3,left:r.enabled?21:3,
                      width:18,height:18,borderRadius:"50%",background:"white",
                      transition:"left 0.2s",boxShadow:"0 1px 4px rgba(0,0,0,0.25)"}}/>}
              </div>
            </div>

            {/* Chips */}
            <div style={{display:"flex",flexWrap:"wrap",gap:6}}>
              {r.override?.impact && (
                <span style={{background:IMPACT[r.override.impact]?.bg||T.surface,
                  color:IMPACT[r.override.impact]?.c||T.secondary,
                  padding:"3px 10px",borderRadius:20,fontSize:11,fontWeight:500}}>
                  → {r.override.impact} impact
                </span>
              )}
              {r.override?.force_route && (
                <span style={{background:T.redLight,color:T.red,
                  padding:"3px 10px",borderRadius:20,fontSize:11,fontWeight:500}}>
                  ⛔ hard block
                </span>
              )}
              {r.override?.reversibility && (
                <span style={{background:T.orangeLight,color:T.orange,
                  padding:"3px 10px",borderRadius:20,fontSize:11,fontWeight:500}}>
                  → {r.override.reversibility}
                </span>
              )}
              {r.override?.add_approvers?.map(a=>(
                <span key={a} style={{background:T.purpleLight,color:T.purple,
                  padding:"3px 10px",borderRadius:20,fontSize:11,fontWeight:500}}>
                  + {a}
                </span>
              ))}
              <span style={{background:T.accentLight,color:T.accent,
                padding:"3px 10px",borderRadius:20,fontSize:11,fontWeight:600,
                marginLeft:"auto",fontVariantNumeric:"tabular-nums"}}>
                ⚡ {r.fired_count||0} times
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const CHART_COLORS = [T.accent,"#34C759","#FF9F0A","#FF3B30","#BF5AF2","#FF6B35","#AEAEB2"];
const tipStyle = {
  contentStyle:{background:T.card,border:`1px solid ${T.border}`,
    borderRadius:10,color:T.text,fontSize:12,boxShadow:T.shadowMd},
};

function AnalyticsPage({api}) {
  const [stats,setStats]         = useState(null);
  const [decisions,setDecisions] = useState([]);
  const [loading,setLoading]     = useState(true);

  useEffect(()=>{
    Promise.all([
      api("/decisions/stats/summary",{role:"admin"}),
      api("/decisions/",{role:"approver"}),
    ]).then(([s,d])=>{ setStats(s); setDecisions(d.decisions||[]); })
    .catch(console.error).finally(()=>setLoading(false));
  },[api]);

  if (loading) return <div style={{display:"flex",justifyContent:"center",padding:80}}><Spin/></div>;

  const statusData = stats
    ? Object.entries(stats).filter(([,v])=>v>0)
        .map(([k,v])=>({name:STATUS[k]?.label||k,value:v,color:STATUS[k]?.c||"#AEAEB2"}))
    : [];

  const impactData = ["low","medium","high","critical"].map(i=>({
    name:i.charAt(0).toUpperCase()+i.slice(1),
    count:decisions.filter(d=>d.classification?.impact===i).length,
    color:IMPACT[i]?.c,fill:IMPACT[i]?.c,
  })).filter(d=>d.count>0);

  const agentCounts = decisions.reduce((a,d)=>{
    const n=fmt.agent(d.agent_id); a[n]=(a[n]||0)+1; return a;
  },{});
  const topAgents = Object.entries(agentCounts).sort((a,b)=>b[1]-a[1]).slice(0,6)
    .map(([name,count])=>({name,count}));

  const total     = decisions.length;
  const completed = decisions.filter(d=>d.status==="completed").length;
  const rolledBack= decisions.filter(d=>d.status==="rolled_back").length;
  const rejected  = decisions.filter(d=>d.status==="rejected").length;

  const card = {background:T.card,borderRadius:16,padding:"20px 22px",boxShadow:T.shadow};
  const sectionLabel = {fontSize:11,color:T.secondary,marginBottom:16,
    textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:600};

  return (
    <div style={{animation:"fadeIn 0.2s ease"}}>
      <h2 style={{fontSize:22,fontWeight:700,color:T.text,
        letterSpacing:"-0.02em",marginBottom:22}}>Analytics</h2>

      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:14,marginBottom:18}}>
        <StatCard label="Total Decisions" value={total}     color={T.accent} accent={T.accent}/>
        <StatCard label="Completed"       value={completed} color={T.green}  accent={T.green}
          sub={total?`${Math.round(completed/total*100)}% success rate`:""}/>
        <StatCard label="Rolled Back"     value={rolledBack} color={T.orange} accent={T.orange}/>
        <StatCard label="Rejected"        value={rejected}  color={T.red}    accent={T.red}/>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14,marginBottom:14}}>
        <div style={card}>
          <div style={sectionLabel}>Status Breakdown</div>
          {statusData.length
            ? <ResponsiveContainer width="100%" height={190}>
                <PieChart>
                  <Pie data={statusData} cx="50%" cy="50%" outerRadius={68} dataKey="value"
                    label={({name,percent})=>`${name} ${(percent*100).toFixed(0)}%`}
                    labelLine={false} fontSize={10}>
                    {statusData.map((e,i)=><Cell key={i} fill={e.color}/>)}
                  </Pie>
                  <Tooltip {...tipStyle}/>
                </PieChart>
              </ResponsiveContainer>
            : <Empty msg="No data yet"/>}
        </div>

        <div style={card}>
          <div style={sectionLabel}>Impact Distribution</div>
          {impactData.length
            ? <ResponsiveContainer width="100%" height={190}>
                <BarChart data={impactData} barSize={30}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.borderLight} vertical={false}/>
                  <XAxis dataKey="name" tick={{fill:T.secondary,fontSize:11}} axisLine={false} tickLine={false}/>
                  <YAxis tick={{fill:T.secondary,fontSize:11}} axisLine={false} tickLine={false}/>
                  <Tooltip {...tipStyle}/>
                  <Bar dataKey="count" radius={[6,6,0,0]}>
                    {impactData.map((e,i)=><Cell key={i} fill={e.color}/>)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            : <Empty msg="No classified decisions yet"/>}
        </div>
      </div>

      <div style={card}>
        <div style={sectionLabel}>Top Agents by Volume</div>
        {topAgents.length ? topAgents.map((a,i)=>(
          <div key={a.name} style={{display:"flex",justifyContent:"space-between",
            alignItems:"center",padding:"10px 0",
            borderBottom:i<topAgents.length-1?`1px solid ${T.borderLight}`:"none"}}>
            <span style={{fontSize:13,color:T.text,fontWeight:500}}>{a.name}</span>
            <div style={{display:"flex",alignItems:"center",gap:12}}>
              <div style={{width:120,height:4,background:T.borderLight,borderRadius:2}}>
                <div style={{width:`${(a.count/topAgents[0].count)*100}%`,height:"100%",
                  background:CHART_COLORS[i%CHART_COLORS.length],borderRadius:2,
                  transition:"width 0.5s ease"}}/>
              </div>
              <span style={{color:T.accent,fontSize:13,fontWeight:600,
                fontVariantNumeric:"tabular-nums",minWidth:20,textAlign:"right"}}>
                {a.count}
              </span>
            </div>
          </div>
        )) : <Empty msg="No decisions yet"/>}
      </div>
    </div>
  );
}

// ─── Config Modal ───────────────────────────────────────────────
function ConfigModal({cfg,onSave}) {
  const [f,setF] = useState({...cfg});
  const set = k => e => setF(p=>({...p,[k]:e.target.value}));

  const inputStyle = {
    width:"100%",background:T.surface,border:`1px solid ${T.border}`,
    borderRadius:8,padding:"10px 13px",color:T.text,fontSize:13,
    outline:"none",transition:"border-color 0.15s",
  };

  return (
    <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.40)",
      display:"flex",alignItems:"center",justifyContent:"center",zIndex:200,
      backdropFilter:"blur(8px)",animation:"fadeIn 0.2s ease"}}>
      <div style={{background:T.bg,borderRadius:20,padding:36,width:420,
        boxShadow:T.shadowLg}}>
        <div style={{fontSize:22,fontWeight:700,color:T.text,
          letterSpacing:"-0.02em",marginBottom:6}}>Connect to ARIA</div>
        <div style={{fontSize:13,color:T.secondary,marginBottom:24,lineHeight:1.55}}>
          Enter your API endpoint and authentication keys to get started.
        </div>
        {[
          ["API URL","url","https://your-app.azurecontainerapps.io","text"],
          ["Agent API Key","agentKey","","password"],
          ["Approver API Key","approverKey","","password"],
          ["Admin API Key","adminKey","","password"],
        ].map(([label,key,ph,type])=>(
          <div key={key} style={{marginBottom:14}}>
            <div style={{fontSize:12,color:T.secondary,marginBottom:5,fontWeight:500}}>{label}</div>
            <input value={f[key]||""} onChange={set(key)} placeholder={ph} type={type}
              style={inputStyle}/>
          </div>
        ))}
        <button onClick={()=>onSave(f)}
          style={{width:"100%",background:T.accent,border:"none",color:"white",
            padding:"12px",borderRadius:10,fontSize:14,fontWeight:600,
            cursor:"pointer",marginTop:8,fontFamily:"inherit",
            boxShadow:"0 4px 12px rgba(0,113,227,0.35)",letterSpacing:"0.01em"}}>
          Connect →
        </button>
      </div>
    </div>
  );
}

// ─── Navigation ─────────────────────────────────────────────────
const NAV = [
  {id:"overview",  label:"Overview",  icon:"○"},
  {id:"decisions", label:"Decisions", icon:"◎"},
  {id:"rules",     label:"Rules",     icon:"◆"},
  {id:"analytics", label:"Analytics", icon:"▦"},
];

const EMPTY_CFG = {url:"",agentKey:"",approverKey:"",adminKey:""};

// ─── App ─────────────────────────────────────────────────────────
export default function App() {
  const [page,setPage]       = useState("overview");
  const [cfg,setCfg]         = useState(EMPTY_CFG);
  const [showCfg,setShowCfg] = useState(true);
  const [jumpId,setJumpId]   = useState(null);

  const saveCfg = c => { setCfg(c); setShowCfg(false); };
  const api = useApi(cfg);

  const handleSelectDecision = id => {
    setJumpId(id); setPage("decisions");
  };

  return (
    <div style={{display:"flex",height:"100vh",background:T.surface,
      fontFamily:"-apple-system,BlinkMacSystemFont,'Inter','SF Pro Text',Helvetica,Arial,sans-serif",
      color:T.text,overflow:"hidden"}}>
      <style>{css}</style>

      {/* Sidebar */}
      <div style={{width:196,background:T.bg,borderRight:`1px solid ${T.border}`,
        display:"flex",flexDirection:"column",flexShrink:0}}>

        {/* Logo */}
        <div style={{padding:"24px 20px 20px"}}>
          <div style={{fontSize:20,fontWeight:700,color:T.text,letterSpacing:"-0.03em"}}>
            ARIA
          </div>
          <div style={{fontSize:10,color:T.tertiary,marginTop:2,
            letterSpacing:"0.1em",textTransform:"uppercase",fontWeight:500}}>
            Control Center
          </div>
        </div>

        <Divider/>

        {/* Nav */}
        <nav style={{flex:1,padding:"12px 10px"}}>
          {NAV.map(n=>(
            <button key={n.id} onClick={()=>setPage(n.id)}
              style={{display:"flex",alignItems:"center",gap:10,width:"100%",
                padding:"9px 12px",borderRadius:8,border:"none",cursor:"pointer",
                background:page===n.id?T.accentLight:"transparent",
                color:page===n.id?T.accent:T.secondary,
                fontSize:13,fontWeight:page===n.id?600:400,
                marginBottom:2,transition:"all 0.15s",textAlign:"left",
                fontFamily:"inherit",letterSpacing:"0.01em"}}>
              <span style={{fontSize:13,opacity:page===n.id?1:0.7}}>{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>

        <Divider/>

        {/* Settings */}
        <div style={{padding:"12px 10px"}}>
          <button onClick={()=>setShowCfg(true)}
            style={{display:"flex",alignItems:"center",gap:10,width:"100%",
              padding:"9px 12px",borderRadius:8,border:"none",cursor:"pointer",
              background:"transparent",color:T.secondary,fontSize:13,
              textAlign:"left",fontFamily:"inherit",fontWeight:400}}>
            <span>⚙</span> Settings
          </button>
          <div style={{padding:"2px 12px",fontSize:11,color:T.tertiary,
            overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
            {cfg.url ? cfg.url.replace("https://","").split(".")[0] : "Not connected"}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div style={{flex:1,display:"flex",flexDirection:"column",
        minWidth:0,overflow:"hidden"}}>

        {/* Top bar */}
        <div style={{padding:"14px 28px",borderBottom:`1px solid ${T.border}`,
          display:"flex",justifyContent:"space-between",alignItems:"center",
          background:T.bg,flexShrink:0}}>
          <div>
            <div style={{fontSize:16,fontWeight:700,color:T.text,
              letterSpacing:"-0.02em"}}>
              {NAV.find(n=>n.id===page)?.label}
            </div>
            <div style={{fontSize:11,color:T.tertiary,marginTop:1,fontWeight:400}}>
              AI Reliability & Integrity Architecture
            </div>
          </div>
          {cfg.url && (
            <a href={`${cfg.url}/docs`} target="_blank" rel="noreferrer"
              style={{background:T.surface,border:`1px solid ${T.border}`,
                color:T.secondary,padding:"7px 14px",borderRadius:8,
                fontSize:12,fontWeight:500,display:"flex",alignItems:"center",gap:5,
                transition:"all 0.15s"}}>
              API Docs ↗
            </a>
          )}
        </div>

        {/* Page content */}
        <div style={{flex:1,overflowY:"auto",padding:"24px 28px"}}>
          {!cfg.url
            ? <div style={{textAlign:"center",padding:"80px 0",animation:"fadeIn 0.3s ease"}}>
                <div style={{width:72,height:72,borderRadius:18,background:T.accentLight,
                  display:"flex",alignItems:"center",justifyContent:"center",
                  fontSize:32,margin:"0 auto 20px"}}>◌</div>
                <div style={{fontSize:20,fontWeight:600,color:T.text,
                  marginBottom:8,letterSpacing:"-0.02em"}}>Connect to ARIA</div>
                <div style={{color:T.secondary,marginBottom:24,fontSize:14}}>
                  Configure your API endpoint and keys to get started
                </div>
                <button onClick={()=>setShowCfg(true)}
                  style={{background:T.accent,border:"none",color:"white",
                    padding:"12px 28px",borderRadius:10,fontSize:14,fontWeight:600,
                    cursor:"pointer",fontFamily:"inherit",
                    boxShadow:"0 4px 12px rgba(0,113,227,0.35)"}}>
                  Open Settings
                </button>
              </div>
            : page==="overview"  ? <OverviewPage  api={api} onSelectDecision={handleSelectDecision}/>
            : page==="decisions" ? <DecisionsPage api={api} initialId={jumpId}/>
            : page==="rules"     ? <RulesPage     api={api}/>
            :                      <AnalyticsPage  api={api}/>
          }
        </div>
      </div>

      {showCfg && <ConfigModal cfg={cfg} onSave={saveCfg}/>}
    </div>
  );
}