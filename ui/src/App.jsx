import { useState, useEffect, useCallback } from "react";
import {
  PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from "recharts";

// ─── Environment config (set in .env) ────────────────────────
const CONFIG = {
  url:         import.meta.env.VITE_API_URL      || "https://ca-aria-dev.purpleisland-b4cd0839.centralus.azurecontainerapps.io",
  adminKey:    import.meta.env.VITE_ADMIN_KEY    || "IWOOhvGQ5giFzjfzhcF7CHm1Sx9g5OF5TNgvsHSqb0E",
  approverKey: import.meta.env.VITE_APPROVER_KEY || "7GykGbcn0G12H4V_AuWpL8ZVC-_YD55N-45MGyMQ0G0",
  agentKey:    import.meta.env.VITE_AGENT_KEY    || "l15_pTbIoFim45Z6LJjtwspDO0tO0rw8E298LcG4olA",
};

// ─── Hardcoded users (3 roles) ───────────────────────────────
const USERS = {
  admin: {
    password: "aria-admin-2026", role: "admin",
    displayName: "Admin", color: "#0071E3",
    apiKey: CONFIG.adminKey,
  },
  approver: {
    password: "aria-approver-2026", role: "approver",
    displayName: "Approver", color: "#34C759",
    apiKey: CONFIG.approverKey,
  },
  tester: {
    password: "aria-tester-2026", role: "tester",
    displayName: "Tester", color: "#FF9F0A",
    apiKey: CONFIG.agentKey,
  },
};

// ─── Role permissions ─────────────────────────────────────────
const PERMS = {
  admin:    { submit:true,  approve:true,  execute:true,  rollback:true,  rules:true,  stats:true,  adminPanel:true,  expireTTL:true  },
  approver: { submit:true,  approve:true,  execute:true,  rollback:false, rules:false, stats:false, adminPanel:false, expireTTL:false },
  tester:   { submit:true,  approve:false, execute:false, rollback:false, rules:false, stats:false, adminPanel:false, expireTTL:false },
};

// ─── Design tokens (Apple-inspired) ──────────────────────────
const T = {
  bg:"#FFFFFF", surface:"#F5F5F7", card:"#FFFFFF",
  border:"#E5E5EA", borderLight:"#F2F2F7",
  accent:"#0071E3", accentLight:"#EBF3FD",
  green:"#34C759", greenLight:"#EDFAF1",
  amber:"#FF9F0A", amberLight:"#FFF5E6",
  red:"#FF3B30", redLight:"#FFECEB",
  orange:"#FF6B35", orangeLight:"#FFF1EB",
  purple:"#BF5AF2", purpleLight:"#F7EFFE",
  text:"#1D1D1F", secondary:"#6E6E73", tertiary:"#AEAEB2",
  shadow:"0 2px 12px rgba(0,0,0,0.07),0 1px 3px rgba(0,0,0,0.04)",
  shadowMd:"0 4px 24px rgba(0,0,0,0.10),0 2px 8px rgba(0,0,0,0.06)",
  shadowLg:"0 20px 60px rgba(0,0,0,0.14),0 4px 16px rgba(0,0,0,0.08)",
};

// ─── Lookup tables ─────────────────────────────────────────────
const STATUS = {
  submitted:        {c:"#6E6E73",bg:"#F5F5F7",label:"Submitted"},
  validating:       {c:"#0071E3",bg:"#EBF3FD",label:"Validating",pulse:true},
  auto_approved:    {c:"#1A8A3A",bg:"#EDFAF1",label:"Auto Approved"},
  pending_approval: {c:"#C47700",bg:"#FFF5E6",label:"Pending",pulse:true},
  approved:         {c:"#1A8A3A",bg:"#EDFAF1",label:"Approved"},
  rejected:         {c:"#CC2020",bg:"#FFECEB",label:"Rejected"},
  executing:        {c:"#0071E3",bg:"#EBF3FD",label:"Executing",pulse:true},
  completed:        {c:"#1A8A3A",bg:"#EDFAF1",label:"Completed"},
  failed:           {c:"#CC2020",bg:"#FFECEB",label:"Failed"},
  rolled_back:      {c:"#CC5500",bg:"#FFF1EB",label:"Rolled Back"},
};
const IMPACT = {
  low:      {c:"#34C759",bg:"#EDFAF1",label:"Low",     w:"25%"},
  medium:   {c:"#FF9F0A",bg:"#FFF5E6",label:"Medium",  w:"50%"},
  high:     {c:"#FF6B35",bg:"#FFF1EB",label:"High",    w:"75%"},
  critical: {c:"#FF3B30",bg:"#FFECEB",label:"Critical",w:"100%"},
};
const EVENT_META = {
  decision_submitted:          {c:"#AEAEB2",sym:"→",label:"Submitted"},
  freshness_check_started:     {c:"#0071E3",sym:"⟳",label:"Freshness Check"},
  freshness_check_passed:      {c:"#34C759",sym:"✓",label:"Data Fresh"},
  freshness_check_failed:      {c:"#FF3B30",sym:"✗",label:"Stale Data"},
  ai_classification_completed: {c:"#BF5AF2",sym:"◈",label:"AI Classified"},
  low_confidence_escalation:   {c:"#FF9F0A",sym:"⚠",label:"Low Confidence — Escalated"},
  rules_engine_applied:        {c:"#FF6B35",sym:"⚡",label:"Rules Overrode AI"},
  rules_engine_no_match:       {c:"#AEAEB2",sym:"—",label:"No Rules Matched"},
  counterfactual_recorded:     {c:"#BF5AF2",sym:"⟷",label:"Counterfactual Logged"},
  classification_finalized:    {c:"#0071E3",sym:"◉",label:"Classification Final"},
  decision_approved:           {c:"#34C759",sym:"✓",label:"Approved"},
  partial_approval_recorded:   {c:"#FF9F0A",sym:"½",label:"Partial Approval"},
  decision_rejected:           {c:"#FF3B30",sym:"✗",label:"Rejected"},
  approval_expired:            {c:"#FF6B35",sym:"⏱",label:"Approval Expired"},
  agent_suspended_block:       {c:"#FF3B30",sym:"⛔",label:"Agent Blocked"},
  probationary_override:       {c:"#FF9F0A",sym:"⚠",label:"Probationary Override"},
  execution_started:           {c:"#0071E3",sym:"▶",label:"Executing"},
  snapshot_captured:           {c:"#BF5AF2",sym:"◎",label:"Snapshot Captured"},
  execution_completed:         {c:"#34C759",sym:"✓",label:"Executed"},
  execution_failed:            {c:"#FF3B30",sym:"✗",label:"Execution Failed"},
  rollback_started:            {c:"#FF6B35",sym:"↩",label:"Rollback Started"},
  rollback_completed:          {c:"#34C759",sym:"↩",label:"Rolled Back"},
  pipeline_error:              {c:"#FF3B30",sym:"!",label:"Pipeline Error"},
};
const ACTION_LABEL = a => ({
  // existing ones...
  wire_transfer:         "Wire Transfer",
  bank_transfer:         "Bank Transfer",
  payment:               "Payment",
  refund:                "Refund",
  send_email:            "Send Email",
  send_reminder_email:   "Send Reminder",
  send_notification:     "Send Notification",
  broadcast_message:     "Broadcast Message",
  modify_document:       "Modify Document",
  update_policy:         "Update Policy",
  create_document:       "Create Document",
  archive_document:      "Archive Document",
  update_payment_status: "Update Payment Status",
  update_payment_terms:  "Update Payment Terms",
  generate_report:       "Generate Report",
  export_data:           "Export Data",
  run_audit:             "Run Audit",
  update_record:         "Update Record",
  create_record:         "Create Record",
  delete_record:         "Delete Record",
  delete_data:           "Delete Data",
  purge:                 "Purge Data",
  archive_record:        "Archive Record",
  deploy_config:         "Deploy Config",
  update_credentials:    "Update Credentials",
  revoke_access:         "Revoke Access",
  grant_access:          "Grant Access",
}[a] || a?.replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase()) || "—");

const fmt = {
  id:    s => s?s.substring(0,8).toUpperCase():"—",
  agent: s => s?.replace(/-v\d+$/,"").replace(/-/g," ").replace(/\b\w/g,c=>c.toUpperCase())||s||"—",
  time:  s => {
    if(!s)return"—";
    const diff=Math.floor((Date.now()-new Date(s))/1000);
    if(diff<60)return`${diff}s ago`;
    if(diff<3600)return`${Math.floor(diff/60)}m ago`;
    if(diff<86400)return`${Math.floor(diff/3600)}h ago`;
    return new Date(s).toLocaleDateString();
  },
  clock: s => s?new Date(s).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit"}):"—",
  dt:    s => s?new Date(s).toLocaleString():"—",
};

// ─── API hook ─────────────────────────────────────────────────
function useApi(apiKey) {
  return useCallback(async (path, opts={}) => {
    const res = await fetch(`${CONFIG.url}${path}`, {
      method: opts.method||"GET",
      headers: {"X-API-Key":apiKey||"","Content-Type":"application/json"},
      body: opts.body?JSON.stringify(opts.body):undefined,
    });
    if(!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return res.json();
  },[apiKey]);
}

// ─── Session helpers ──────────────────────────────────────────
function saveSession(username, role) {
  const session = {username,role,loginAt:new Date().toISOString()};
  localStorage.setItem("aria_session", JSON.stringify(session));
  const history = JSON.parse(localStorage.getItem("aria_history")||"[]");
  history.unshift(session);
  localStorage.setItem("aria_history", JSON.stringify(history.slice(0,100)));
}
function clearSession() { localStorage.removeItem("aria_session"); }
function getSession()   {
  try { return JSON.parse(localStorage.getItem("aria_session")); }
  catch { return null; }
}
function getHistory()   {
  try { return JSON.parse(localStorage.getItem("aria_history")||"[]"); }
  catch { return []; }
}

// ─── Global styles ─────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:#F5F5F7;font-family:-apple-system,BlinkMacSystemFont,'Inter',Helvetica,Arial,sans-serif;}
  ::-webkit-scrollbar{width:5px;}
  ::-webkit-scrollbar-thumb{background:#D2D2D7;border-radius:10px;}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.35}}
  @keyframes spin{to{transform:rotate(360deg)}}
  @keyframes slideIn{from{transform:translateX(24px);opacity:0}to{transform:translateX(0);opacity:1}}
  @keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
  input::placeholder,textarea::placeholder{color:#AEAEB2;}
  button,select,input,textarea{font-family:inherit;}
  select option{background:#fff;}
`;

// ─── Atoms ─────────────────────────────────────────────────────
const Spin = () => (
  <div style={{width:16,height:16,border:"2px solid #E5E5EA",
    borderTopColor:T.accent,borderRadius:"50%",animation:"spin 0.75s linear infinite"}}/>
);
const Empty = ({msg}) => (
  <div style={{textAlign:"center",padding:"48px 0"}}>
    <div style={{fontSize:28,marginBottom:10,opacity:0.25}}>○</div>
    <div style={{fontSize:13,color:T.secondary}}>{msg}</div>
  </div>
);
const Divider = () => <div style={{height:1,background:T.border}}/>;
const Badge = ({status}) => {
  const s=STATUS[status]||{c:"#6E6E73",bg:"#F5F5F7",label:status};
  return(
    <span style={{background:s.bg,color:s.c,padding:"3px 10px",borderRadius:20,
      fontSize:11,fontWeight:600,display:"inline-flex",alignItems:"center",gap:5,whiteSpace:"nowrap"}}>
      {s.pulse&&<span style={{width:5,height:5,borderRadius:"50%",background:s.c,
        animation:"pulse 1.5s infinite",display:"inline-block"}}/>}
      {s.label}
    </span>
  );
};
const ImpactBadge = ({impact}) => {
  const i=IMPACT[impact]||{c:T.secondary,bg:T.surface,label:impact||"—"};
  return<span style={{background:i.bg,color:i.c,padding:"3px 10px",
    borderRadius:20,fontSize:11,fontWeight:600}}>{i.label}</span>;
};
const ImpactBar = ({impact}) => {
  const i=IMPACT[impact]||{c:T.tertiary,label:impact||"—",w:"0%"};
  return(
    <div style={{display:"flex",alignItems:"center",gap:8}}>
      <div style={{width:56,height:3,background:"#E5E5EA",borderRadius:2,overflow:"hidden"}}>
        <div style={{width:i.w,height:"100%",background:i.c,borderRadius:2}}/>
      </div>
      <span style={{color:i.c,fontSize:11,fontWeight:600}}>{i.label}</span>
    </div>
  );
};
const StatCard = ({label,value,sub,color,accent}) => (
  <div style={{background:T.card,borderRadius:16,padding:"20px 22px",boxShadow:T.shadow,
    position:"relative",overflow:"hidden"}}>
    <div style={{position:"absolute",top:-10,right:-10,width:72,height:72,borderRadius:"50%",
      background:`${accent||color||T.accent}08`}}/>
    <div style={{fontSize:11,color:T.secondary,marginBottom:8,fontWeight:500,
      letterSpacing:"0.02em",textTransform:"uppercase"}}>{label}</div>
    <div style={{fontSize:30,fontWeight:700,color:color||T.text,
      lineHeight:1,letterSpacing:"-0.02em"}}>{value??0}</div>
    {sub&&<div style={{fontSize:12,color:T.secondary,marginTop:5}}>{sub}</div>}
  </div>
);

// Locked button for lower-permission roles
const LockedBtn = ({label, reason}) => (
  <div title={reason} style={{display:"inline-flex",alignItems:"center",gap:6,
    padding:"9px 16px",borderRadius:8,background:T.surface,color:T.tertiary,
    fontSize:13,fontWeight:500,cursor:"not-allowed",userSelect:"none",
    border:`1px solid ${T.border}`}}>
    🔒 {label}
  </div>
);

// Input style reused everywhere
const IS = {background:T.surface,border:`1px solid ${T.border}`,borderRadius:8,
  padding:"9px 12px",color:T.text,fontSize:13,outline:"none",width:"100%"};

// ─── Audit Timeline ─────────────────────────────────────────────
const AuditTimeline = ({events}) => (
  <div>
    {events.map((e,i)=>{
      const m=EVENT_META[e.event_type]||{c:T.tertiary,sym:"·",label:e.event_type};
      return(
        <div key={e.id||i} style={{display:"flex",gap:12,position:"relative"}}>
          {i<events.length-1&&<div style={{position:"absolute",left:14,top:30,
            width:1,height:"calc(100% + 4px)",background:T.border}}/>}
          <div style={{width:28,height:28,borderRadius:"50%",flexShrink:0,
            background:`${m.c}15`,border:`1.5px solid ${m.c}40`,zIndex:1,marginTop:2,
            display:"flex",alignItems:"center",justifyContent:"center",
            fontSize:11,color:m.c,fontWeight:600}}>{m.sym}</div>
          <div style={{flex:1,paddingBottom:14}}>
            <div style={{display:"flex",justifyContent:"space-between",gap:8}}>
              <div style={{fontSize:13,fontWeight:500,color:T.text}}>{m.label}</div>
              <div style={{fontSize:10,color:T.tertiary,whiteSpace:"nowrap",
                fontVariantNumeric:"tabular-nums"}}>{fmt.clock(e.timestamp)}</div>
            </div>
            <div style={{fontSize:11,color:T.secondary,marginTop:1}}>{e.actor}</div>
            {e.details&&Object.keys(e.details).length>0&&(
              <div style={{marginTop:7,padding:"8px 10px",background:T.surface,
                borderRadius:8,border:`1px solid ${T.border}`}}>
                {Object.entries(e.details).slice(0,6).map(([k,v])=>(
                  <div key={k} style={{display:"flex",gap:10,fontSize:11,marginBottom:2}}>
                    <span style={{color:T.secondary,minWidth:110,flexShrink:0}}>{k}</span>
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
const DetailPanel = ({d,audit,loading,onClose,onAction,perms}) => {
  const [approver,setApprover] = useState("");
  const [reason,setReason]     = useState("");
  const [mode,setMode]         = useState(null);
  const [acting,setActing]     = useState(false);
  const [err,setErr]           = useState("");

  const doAction = async()=>{
    setErr("");setActing(true);
    try{await onAction(mode,{approver_id:approver,reason,requested_by:approver});setMode(null);}
    catch(e){setErr(e.message);}
    setActing(false);
  };

  if(!d)return null;
  const clf=d.classification;

  const ActionBtn = ({action,color,bg,label,perm,reason:lockReason})=>{
    if(!perm)return<LockedBtn label={label} reason={lockReason||"Insufficient permissions"}/>;
    return(
      <button onClick={()=>setMode(action)}
        style={{padding:"9px 16px",borderRadius:8,border:bg?"none":`1px solid ${T.border}`,
          background:bg||T.bg,color:bg?"white":color,fontSize:13,fontWeight:600,
          cursor:"pointer",boxShadow:bg?T.shadow:"none"}}>
        {label}
      </button>
    );
  };

  return(
    <div style={{position:"fixed",right:0,top:0,bottom:0,width:520,
      background:T.bg,borderLeft:`1px solid ${T.border}`,display:"flex",
      flexDirection:"column",zIndex:100,boxShadow:T.shadowLg,animation:"slideIn 0.22s ease"}}>

      {/* Header */}
      <div style={{padding:"18px 22px",borderBottom:`1px solid ${T.border}`,
        display:"flex",justifyContent:"space-between",alignItems:"center",flexShrink:0}}>
        <div>
          <div style={{fontSize:10,color:T.secondary,marginBottom:3,
            textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:500}}>Decision Detail</div>
          <span style={{fontSize:13,color:T.accent,fontWeight:500,
            fontVariantNumeric:"tabular-nums"}}>{fmt.id(d.decision_id)}</span>
          <span style={{color:T.tertiary,fontSize:11,marginLeft:10}}>{fmt.time(d.submitted_at)}</span>
        </div>
        <button onClick={onClose} style={{background:T.surface,border:`1px solid ${T.border}`,
          color:T.secondary,width:30,height:30,borderRadius:8,cursor:"pointer",
          fontSize:15,display:"flex",alignItems:"center",justifyContent:"center"}}>×</button>
      </div>

      <div style={{flex:1,overflowY:"auto",padding:"0 22px 32px"}}>

        {/* Status + Impact */}
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginTop:18}}>
          <div style={{background:T.surface,borderRadius:12,padding:"12px 14px"}}>
            <div style={{fontSize:9,color:T.secondary,marginBottom:7,
              textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:500}}>Status</div>
            <Badge status={d.status}/>
          </div>
          <div style={{background:T.surface,borderRadius:12,padding:"12px 14px"}}>
            <div style={{fontSize:9,color:T.secondary,marginBottom:8,
              textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:500}}>Impact</div>
            {clf?.impact?<ImpactBar impact={clf.impact}/>
              :<span style={{color:T.tertiary,fontSize:11}}>Classifying…</span>}
          </div>
        </div>

        {/* Info */}
        <div style={{marginTop:12,background:T.surface,borderRadius:12,overflow:"hidden"}}>
          {[
            ["Action",     ACTION_LABEL(d.action_type),T.text],
            ["Agent",      fmt.agent(d.agent_id),T.text],
            ["Description",d.description,T.text],
            ["Route",      clf?.route?.replace(/_/g," "),T.accent],
            ["Confidence", clf?.confidence!=null?`${(clf.confidence*100).toFixed(0)}%`:null,T.text],
            ["Approvers",  clf?.suggested_approvers?.join(", "),T.text],
            ["Expires",    d.expires_at?fmt.time(d.expires_at):null,T.text],
          ].map(([k,v,c],i,a)=>(
            <div key={k} style={{display:"flex",gap:12,padding:"9px 14px",
              borderBottom:i<a.length-1?`1px solid ${T.border}`:"none"}}>
              <span style={{color:T.secondary,fontSize:12,width:90,flexShrink:0,paddingTop:1}}>{k}</span>
              <span style={{color:c,fontSize:13,wordBreak:"break-word"}}>{v||"—"}</span>
            </div>
          ))}
        </div>

        {/* Risk reason */}
        {clf?.risk_reason&&(
          <div style={{marginTop:10,padding:"12px 14px",background:T.amberLight,
            borderRadius:12,borderLeft:`3px solid ${T.amber}`}}>
            <div style={{fontSize:9,color:T.amber,marginBottom:5,
              textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:600}}>Risk Reason</div>
            <div style={{fontSize:13,color:T.text,lineHeight:1.65}}>{clf.risk_reason}</div>
          </div>
        )}

        {/* Counterfactual */}
        {d.counterfactual&&(
          <div style={{marginTop:10,padding:"12px 14px",background:T.purpleLight,
            borderRadius:12,borderLeft:`3px solid ${T.purple}`}}>
            <div style={{fontSize:9,color:T.purple,marginBottom:10,
              textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:600}}>Counterfactual</div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:8}}>
              {["without_rules_engine","with_rules_engine"].map(k=>(
                <div key={k} style={{background:"rgba(255,255,255,0.7)",borderRadius:8,padding:"8px 10px"}}>
                  <div style={{fontSize:9,color:T.secondary,marginBottom:4}}>
                    {k==="without_rules_engine"?"Without Rules":"With Rules"}</div>
                  <div style={{fontSize:12,fontWeight:600,color:T.text}}>
                    {d.counterfactual[k]?.route?.replace(/_/g," ")||"—"}</div>
                  <div style={{fontSize:11,color:T.secondary}}>{d.counterfactual[k]?.impact}</div>
                </div>
              ))}
            </div>
            <div style={{fontSize:12,color:T.text,lineHeight:1.6}}>{d.counterfactual.summary}</div>
          </div>
        )}

        {/* Payload */}
        {d.payload&&Object.keys(d.payload).length>0&&(
          <div style={{marginTop:10}}>
            <div style={{fontSize:9,color:T.secondary,marginBottom:7,
              textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:500}}>Payload</div>
            <div style={{background:T.surface,borderRadius:12,padding:"10px 14px",
              fontSize:12,color:T.text,lineHeight:1.8}}>
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
        {["pending_approval","approved","auto_approved","completed"].includes(d.status)&&(
          <div style={{marginTop:16}}>
            <div style={{fontSize:9,color:T.secondary,marginBottom:10,
              textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:500}}>Actions</div>

            {err&&<div style={{marginBottom:10,padding:"8px 12px",background:T.redLight,
              borderRadius:8,fontSize:12,color:T.red}}>{err}</div>}

            {mode?(
              <div style={{display:"flex",flexDirection:"column",gap:8}}>
                <input value={approver} onChange={e=>setApprover(e.target.value)}
                  placeholder="Your name or email" style={IS}/>
                {(mode==="reject"||mode==="rollback")&&(
                  <input value={reason} onChange={e=>setReason(e.target.value)}
                    placeholder={mode==="reject"?"Rejection reason":"Rollback reason"} style={IS}/>
                )}
                <div style={{display:"flex",gap:8}}>
                  <button onClick={doAction} disabled={acting}
                    style={{flex:1,padding:"10px",borderRadius:8,border:"none",fontWeight:600,
                      fontSize:13,cursor:acting?"not-allowed":"pointer",
                      background:mode==="reject"?T.red:T.accent,color:"white",
                      opacity:acting?0.6:1}}>
                    {acting?"Processing…":`Confirm ${mode.charAt(0).toUpperCase()+mode.slice(1)}`}
                  </button>
                  <button onClick={()=>{setMode(null);setErr("");}}
                    style={{padding:"10px 16px",borderRadius:8,border:`1px solid ${T.border}`,
                      background:T.surface,color:T.secondary,fontSize:13,cursor:"pointer",fontWeight:500}}>
                    Cancel
                  </button>
                </div>
              </div>
            ):(
              <div style={{display:"flex",flexWrap:"wrap",gap:8}}>
                {d.status==="pending_approval"&&<>
                  <ActionBtn action="approve" bg={T.green} label="✓ Approve"
                    perm={perms.approve} lockReason="Requires Approver role"/>
                  <ActionBtn action="reject" color={T.red} label="✗ Reject"
                    perm={perms.approve} lockReason="Requires Approver role"/>
                </>}
                {(d.status==="approved"||d.status==="auto_approved")&&
                  <ActionBtn action="execute" bg={T.accent} label="▶ Execute"
                    perm={perms.execute} lockReason="Requires Approver role"/>}
                {d.status==="completed"&&d.rollback_available&&
                  <ActionBtn action="rollback" color={T.orange} label="↩ Rollback"
                    perm={perms.rollback} lockReason="Requires Admin role"/>}
              </div>
            )}
          </div>
        )}

        {/* Audit trail */}
        <div style={{marginTop:22}}>
          <div style={{fontSize:9,color:T.secondary,marginBottom:14,
            textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:500}}>
            Pipeline Trail · {audit.length} events
          </div>
          {loading?<div style={{display:"flex",justifyContent:"center",padding:30}}><Spin/></div>
            :audit.length?<AuditTimeline events={audit}/>:<Empty msg="No events yet"/>}
        </div>
      </div>
    </div>
  );
};

// ─── Submit Decision Modal ─────────────────────────────────────
const SubmitModal = ({api,onClose,onDone}) => {
  const [form,setForm] = useState({
    agent_id:"",action_type:"generate_report",
    description:"",context:"",payload:"{}",
  });
  const [loading,setLoading] = useState(false);
  const [err,setErr]         = useState("");
  const set = k=>e=>setForm(p=>({...p,[k]:e.target.value}));

  const submit = async()=>{
    setErr(""); setLoading(true);
    try{
      let payload={};
      try{payload=JSON.parse(form.payload);}
      catch{setErr("Payload must be valid JSON");setLoading(false);return;}
      await api("/decisions/submit",{method:"POST",body:{
        agent_id:form.agent_id,action_type:form.action_type,
        description:form.description,context:form.context,payload,
      }});
      onDone(); onClose();
    }catch(e){setErr(e.message);}
    setLoading(false);
  };

  const ACTION_TYPES = [
  // Reports & Read
  "generate_report",
  "export_data",
  "run_audit",

  // Communication
  "send_email",
  "send_reminder_email",
  "send_notification",
  "broadcast_message",

  // Documents
  "modify_document",
  "update_policy",
  "create_document",
  "archive_document",

  // Payments & Finance
  "wire_transfer",
  "bank_transfer",
  "payment",
  "refund",
  "update_payment_status",
  "update_payment_terms",

  // Data Operations
  "update_record",
  "update_payment_status",
  "create_record",
  "delete_record",
  "delete_data",
  "purge",
  "archive_record",

  // System
  "deploy_config",
  "update_credentials",
  "revoke_access",
  "grant_access",
];

  return(
    <Modal title="Submit Decision" sub="Submit an AI action for ARIA to evaluate" onClose={onClose}>
      {err&&<ErrBox msg={err}/>}
      {[["Agent ID","agent_id","text","e.g. payment-agent-v1"],
        ["Description","description","text","What is the agent trying to do?"],
        ["Context","context","text","Business context or reason (optional)"],
      ].map(([l,k,t,p])=>(
        <Field key={k} label={l}>
          <input value={form[k]} onChange={set(k)} placeholder={p} type={t} style={IS}/>
        </Field>
      ))}
      <Field label="Action Type">
        <select value={form.action_type} onChange={set("action_type")}
          style={{...IS,cursor:"pointer"}}>
          {ACTION_TYPES.map(a=><option key={a} value={a}>{ACTION_LABEL(a)}</option>)}
        </select>
      </Field>
      <Field label="Payload (JSON)">
        <textarea value={form.payload} onChange={set("payload")} rows={3}
          placeholder='{"amount":5000,"vendor_id":"ACC-101"}'
          style={{...IS,resize:"vertical",lineHeight:1.6,fontFamily:"'SF Mono',monospace"}}/>
      </Field>
      <PrimaryBtn onClick={submit} loading={loading} label="Submit Decision →"/>
    </Modal>
  );
};

// ─── Create Rule Modal ─────────────────────────────────────────
const CreateRuleModal = ({api,onClose,onDone}) => {
  const [form,setForm] = useState({
    name:"",description:"",created_by:"",
    action_types:"",payload_field:"",operator:"gt",value:"",description_contains:"",
    impact:"",reversibility:"",force_route:"",add_approvers:"",reason:"",
  });
  const [loading,setLoading] = useState(false);
  const [err,setErr]         = useState("");
  const set = k=>e=>setForm(p=>({...p,[k]:e.target.value}));

  const submit = async()=>{
    setErr("");setLoading(true);
    try{
      const condition={};
      if(form.action_types) condition.action_types=form.action_types.split(",").map(s=>s.trim()).filter(Boolean);
      if(form.payload_field){condition.payload_field=form.payload_field;condition.operator=form.operator;condition.value=parseFloat(form.value)||form.value;}
      if(form.description_contains) condition.description_contains=form.description_contains;
      const override={};
      if(form.impact)        override.impact=form.impact;
      if(form.reversibility) override.reversibility=form.reversibility;
      if(form.force_route)   override.force_route=form.force_route;
      if(form.add_approvers) override.add_approvers=form.add_approvers.split(",").map(s=>s.trim()).filter(Boolean);
      if(form.reason)        override.reason=form.reason;
      await api("/rules/",{method:"POST",body:{
        name:form.name,description:form.description,
        created_by:form.created_by,condition,override,
      }});
      onDone();onClose();
    }catch(e){setErr(e.message);}
    setLoading(false);
  };

  return(
    <Modal title="Create Rule" sub="Define a new business rule for the rules engine" onClose={onClose}>
      {err&&<ErrBox msg={err}/>}
      {[["Rule Name","name","e.g. large_transfer_threshold"],
        ["Description","description","What does this rule do?"],
        ["Created By","created_by","Your email"],
      ].map(([l,k,p])=>(
        <Field key={k} label={l}>
          <input value={form[k]} onChange={set(k)} placeholder={p} style={IS}/>
        </Field>
      ))}

      <SLabel>Conditions (all filled fields must match)</SLabel>

      <Field label="Action Types (comma-separated)">
        <input value={form.action_types} onChange={set("action_types")}
          placeholder="wire_transfer, payment" style={IS}/>
      </Field>
      <div style={{display:"grid",gridTemplateColumns:"1fr 90px 1fr",gap:8,marginBottom:12}}>
        <Field label="Payload Field">
          <input value={form.payload_field} onChange={set("payload_field")} placeholder="amount" style={IS}/>
        </Field>
        <Field label="Operator">
          <select value={form.operator} onChange={set("operator")} style={{...IS,cursor:"pointer"}}>
            {["gt","gte","lt","lte","eq"].map(o=><option key={o} value={o}>{o}</option>)}
          </select>
        </Field>
        <Field label="Value">
          <input value={form.value} onChange={set("value")} placeholder="10000" style={IS}/>
        </Field>
      </div>
      <Field label="Description Contains">
        <input value={form.description_contains} onChange={set("description_contains")}
          placeholder="policy" style={IS}/>
      </Field>

      <SLabel>Overrides (what changes when rule fires)</SLabel>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:12}}>
        <Field label="Escalate Impact To">
          <select value={form.impact} onChange={set("impact")} style={{...IS,cursor:"pointer"}}>
            <option value="">No change</option>
            {["low","medium","high","critical"].map(i=>(
              <option key={i} value={i}>{i.charAt(0).toUpperCase()+i.slice(1)}</option>
            ))}
          </select>
        </Field>
        <Field label="Force Route">
          <select value={form.force_route} onChange={set("force_route")} style={{...IS,cursor:"pointer"}}>
            <option value="">No override</option>
            <option value="hard_block">Hard Block</option>
          </select>
        </Field>
      </div>
      <Field label="Add Approvers (comma-separated)">
        <input value={form.add_approvers} onChange={set("add_approvers")}
          placeholder="Finance Manager, CFO" style={IS}/>
      </Field>
      <Field label="Reason">
        <input value={form.reason} onChange={set("reason")}
          placeholder="Transfer exceeds threshold." style={IS}/>
      </Field>
      <PrimaryBtn onClick={submit} loading={loading} label="Create Rule →"/>
    </Modal>
  );
};

// ─── Shared Modal Primitives ───────────────────────────────────
const Modal = ({title,sub,onClose,children}) => (
  <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.4)",
    display:"flex",alignItems:"center",justifyContent:"center",
    zIndex:200,backdropFilter:"blur(8px)",animation:"fadeIn 0.2s ease"}}>
    <div style={{background:T.bg,borderRadius:20,padding:36,width:480,
      boxShadow:T.shadowLg,maxHeight:"90vh",overflowY:"auto"}}>
      <div style={{display:"flex",justifyContent:"space-between",
        alignItems:"flex-start",marginBottom:22}}>
        <div>
          <div style={{fontSize:20,fontWeight:700,color:T.text,
            letterSpacing:"-0.02em",marginBottom:4}}>{title}</div>
          <div style={{fontSize:13,color:T.secondary}}>{sub}</div>
        </div>
        <button onClick={onClose}
          style={{background:T.surface,border:`1px solid ${T.border}`,color:T.secondary,
            width:30,height:30,borderRadius:8,cursor:"pointer",fontSize:15,
            display:"flex",alignItems:"center",justifyContent:"center"}}>×</button>
      </div>
      {children}
    </div>
  </div>
);
const Field = ({label,children}) => (
  <div style={{marginBottom:12}}>
    <div style={{fontSize:12,color:T.secondary,marginBottom:4,fontWeight:500}}>{label}</div>
    {children}
  </div>
);
const SLabel = ({children}) => (
  <div style={{fontSize:10,color:T.secondary,fontWeight:600,textTransform:"uppercase",
    letterSpacing:"0.07em",margin:"18px 0 12px",paddingTop:12,
    borderTop:`1px solid ${T.border}`}}>{children}</div>
);
const ErrBox = ({msg}) => (
  <div style={{marginBottom:14,padding:"10px 14px",background:T.redLight,
    borderRadius:8,fontSize:13,color:T.red}}>{msg}</div>
);
const PrimaryBtn = ({onClick,loading,label}) => (
  <button onClick={onClick} disabled={loading}
    style={{width:"100%",background:T.accent,border:"none",color:"white",
      padding:"12px",borderRadius:10,fontSize:14,fontWeight:600,
      cursor:loading?"not-allowed":"pointer",marginTop:8,opacity:loading?0.7:1,
      boxShadow:"0 4px 12px rgba(0,113,227,0.35)"}}>
    {loading?"Processing…":label}
  </button>
);

// ─── Decision Table ─────────────────────────────────────────────
const COLS="80px 1fr 120px 100px 110px 68px";
const HEADERS=["ID","Action","Agent","Impact","Status","Time"];
const TableHead = () => (
  <div style={{display:"grid",gridTemplateColumns:COLS,gap:14,
    padding:"9px 20px",borderBottom:`1px solid ${T.border}`}}>
    {HEADERS.map(h=><div key={h} style={{fontSize:11,color:T.secondary,fontWeight:500}}>{h}</div>)}
  </div>
);
const DecisionRow = ({d,onClick,selected}) => (
  <div onClick={onClick} style={{display:"grid",gridTemplateColumns:COLS,
    alignItems:"center",gap:14,padding:"12px 20px",cursor:"pointer",
    background:selected?T.accentLight:"transparent",
    borderLeft:selected?`3px solid ${T.accent}`:"3px solid transparent",
    borderBottom:`1px solid ${T.borderLight}`,transition:"all 0.12s"}}>
    <span style={{fontSize:12,color:T.accent,fontWeight:500,
      fontVariantNumeric:"tabular-nums"}}>{fmt.id(d.decision_id)}</span>
    <div>
      <div style={{color:T.text,fontSize:13,fontWeight:500,marginBottom:1}}>
        {ACTION_LABEL(d.action_type)}</div>
      <div style={{color:T.secondary,fontSize:11,overflow:"hidden",
        textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:260}}>{d.description}</div>
    </div>
    <div style={{color:T.secondary,fontSize:12}}>{fmt.agent(d.agent_id)}</div>
    <div>{d.classification?.impact?<ImpactBadge impact={d.classification.impact}/>
      :<span style={{color:T.tertiary,fontSize:11}}>—</span>}</div>
    <Badge status={d.status}/>
    <div style={{color:T.tertiary,fontSize:11,textAlign:"right",
      fontVariantNumeric:"tabular-nums"}}>{fmt.time(d.submitted_at)}</div>
  </div>
);

// ─── Pages ─────────────────────────────────────────────────────

function OverviewPage({api,perms,onSelectDecision}) {
  const [stats,setStats]     = useState(null);
  const [recent,setRecent]   = useState([]);
  const [healthy,setHealthy] = useState(null);
  const [loading,setLoading] = useState(true);

  const load = useCallback(async()=>{
    try{
      const [s,d,h]=await Promise.all([
        api("/decisions/stats/summary"),
        api("/decisions/"),
        api("/health"),
      ]);
      setStats(s);setRecent(d.decisions?.slice(0,10)||[]);setHealthy(!!h.status);
    }catch(e){console.error(e);setHealthy(false);}
    finally{setLoading(false);}
  },[api]);

  useEffect(()=>{load();const t=setInterval(load,15000);return()=>clearInterval(t);},[load]);

  const pending   = stats?.pending_approval||0;
  const completed = stats?.completed||0;
  const rejected  = (stats?.rejected||0)+(stats?.failed||0);
  const total     = stats?Object.values(stats).reduce((a,b)=>a+b,0):0;

  return(
    <div style={{animation:"fadeIn 0.2s ease"}}>
      {/* Status bar */}
      <div style={{display:"inline-flex",alignItems:"center",gap:8,marginBottom:22,
        padding:"9px 16px",background:T.card,borderRadius:10,boxShadow:T.shadow}}>
        {healthy===null?<Spin/>:(
          <div style={{width:7,height:7,borderRadius:"50%",
            background:healthy?T.green:T.red}}/>
        )}
        <span style={{fontSize:12,color:T.secondary}}>
          {healthy===null?"Checking…":healthy?"System operational":"Cannot reach API"}
        </span>
        <span style={{color:T.border}}>·</span>
        <span style={{fontSize:11,color:T.tertiary}}>Auto-refreshes every 15s</span>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:22}}>
        <StatCard label="Awaiting Approval" value={pending}   color={pending>0?T.amber:T.green} accent={T.amber}
          sub={pending>0?"Needs your review":"All clear"}/>
        <StatCard label="Total Decisions"   value={total}     color={T.accent}  accent={T.accent}/>
        <StatCard label="Completed"         value={completed} color={T.green}   accent={T.green}/>
        <StatCard label="Rejected"          value={rejected}  color={T.red}     accent={T.red}/>
      </div>

      <div style={{background:T.card,borderRadius:16,boxShadow:T.shadow,overflow:"hidden"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",
          padding:"14px 20px"}}>
          <div style={{fontSize:15,fontWeight:600,color:T.text}}>Recent Decisions</div>
          <button onClick={load} style={{background:"none",border:"none",
            color:T.secondary,cursor:"pointer",fontSize:13,fontWeight:500}}>↻ Refresh</button>
        </div>
        <Divider/>
        <TableHead/>
        {loading?<div style={{display:"flex",justifyContent:"center",padding:48}}><Spin/></div>
          :recent.length?recent.map(d=><DecisionRow key={d.decision_id} d={d}
              onClick={()=>onSelectDecision(d.decision_id)}/>)
          :<Empty msg="No decisions yet"/>}
      </div>
    </div>
  );
}

function DecisionsPage({api,perms,initialId}) {
  const [all,setAll]           = useState([]);
  const [loading,setLoading]   = useState(true);
  const [search,setSearch]     = useState("");
  const [statusF,setStatusF]   = useState("all");
  const [selected,setSelected] = useState(initialId||null);
  const [detail,setDetail]     = useState(null);
  const [audit,setAudit]       = useState([]);
  const [dLoad,setDLoad]       = useState(false);
  const [showSubmit,setShowSubmit] = useState(false);
  const [refreshKey,setRefreshKey] = useState(0);

  const load = useCallback(async()=>{
    try{const d=await api("/decisions/");setAll(d.decisions||[]);}
    catch(e){console.error(e);}
    finally{setLoading(false);}
  },[api]);

  useEffect(()=>{load();},[load,refreshKey]);

  const select = useCallback(async id=>{
    setSelected(id);setDLoad(true);
    try{
      const [d,a]=await Promise.all([
        api(`/decisions/${id}`),
        api(`/decisions/${id}/audit`),
      ]);
      setDetail(d);setAudit(a.events||[]);
    }catch(e){console.error(e);}
    setDLoad(false);
  },[api]);

  useEffect(()=>{if(initialId)select(initialId);},[initialId]);

  const doAction = useCallback(async(type,body)=>{
    const bM={
      approve:{approver_id:body.approver_id,reason:body.reason},
      reject: {approver_id:body.approver_id,reason:body.reason},
      execute:{requested_by:body.requested_by},
      rollback:{requested_by:body.requested_by,reason:body.reason},
    };
    await api(`/decisions/${selected}/${type}`,{method:"POST",body:bM[type]});
    await select(selected);
    setRefreshKey(k=>k+1);
  },[selected,api,select]);

  const filtered=all.filter(d=>{
    if(statusF!=="all"&&d.status!==statusF)return false;
    if(search&&![d.agent_id,d.action_type,d.description,d.decision_id]
      .some(v=>v?.toLowerCase().includes(search.toLowerCase())))return false;
    return true;
  });

  return(
    <div style={{display:"flex",gap:0,position:"relative",animation:"fadeIn 0.2s ease"}}>
      <div style={{flex:1,minWidth:0}}>
        {/* Toolbar */}
        <div style={{display:"flex",gap:8,marginBottom:14,alignItems:"center"}}>
          <input value={search} onChange={e=>setSearch(e.target.value)}
            placeholder="Search by agent, action, description, or ID…"
            style={{...IS,flex:1,width:"auto"}}/>
          <select value={statusF} onChange={e=>setStatusF(e.target.value)}
            style={{...IS,width:"auto",cursor:"pointer"}}>
            <option value="all">All Statuses</option>
            {Object.entries(STATUS).map(([k,v])=>(
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
          <button onClick={load} style={{...IS,width:"auto",cursor:"pointer",
            color:T.secondary,background:T.surface}}>↻</button>
          <span style={{fontSize:11,color:T.secondary,whiteSpace:"nowrap"}}>
            {filtered.length}/{all.length}
          </span>
          <button onClick={()=>setShowSubmit(true)}
            style={{background:T.accent,border:"none",color:"white",padding:"8px 16px",
              borderRadius:8,fontSize:13,fontWeight:600,cursor:"pointer",
              whiteSpace:"nowrap",boxShadow:"0 2px 8px rgba(0,113,227,0.3)"}}>
            + Submit Decision
          </button>
        </div>

        <div style={{background:T.card,borderRadius:16,boxShadow:T.shadow,overflow:"hidden"}}>
          <TableHead/>
          {loading?<div style={{display:"flex",justifyContent:"center",padding:48}}><Spin/></div>
            :filtered.length?filtered.map(d=><DecisionRow key={d.decision_id} d={d}
                selected={d.decision_id===selected}
                onClick={()=>select(d.decision_id)}/>)
            :<Empty msg="No decisions match your filters"/>}
        </div>
      </div>

      {selected&&(
        <DetailPanel d={detail} audit={audit} loading={dLoad} perms={perms}
          onClose={()=>{setSelected(null);setDetail(null);setAudit([]);}}
          onAction={doAction}/>
      )}

      {showSubmit&&(
        <SubmitModal api={api}
          onClose={()=>setShowSubmit(false)}
          onDone={()=>setRefreshKey(k=>k+1)}/>
      )}
    </div>
  );
}

function RulesPage({api,perms}) {
  const [rules,setRules]       = useState([]);
  const [loading,setLoading]   = useState(true);
  const [toggling,setToggling] = useState(null);
  const [showCreate,setShowCreate] = useState(false);
  const [refreshKey,setRefreshKey] = useState(0);

  const load = useCallback(async()=>{
    try{const d=await api("/rules/");setRules(d.rules||[]);}
    catch(e){console.error(e);}
    finally{setLoading(false);}
  },[api]);

  useEffect(()=>{load();},[load,refreshKey]);

  const toggle = async r=>{
    if(!perms.rules){alert("Requires Admin role");return;}
    setToggling(r.rule_id);
    try{
      await api(`/rules/${r.rule_id}/${r.enabled?"disable":"enable"}`,{method:"PATCH"});
      setRules(p=>p.map(x=>x.rule_id===r.rule_id?{...x,enabled:!x.enabled}:x));
    }catch(e){console.error(e);}
    setToggling(null);
  };

  if(loading)return<div style={{display:"flex",justifyContent:"center",padding:80}}><Spin/></div>;
  const active=rules.filter(r=>r.enabled).length;

  return(
    <div style={{animation:"fadeIn 0.2s ease"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:22}}>
        <div>
          <h2 style={{fontSize:20,fontWeight:700,color:T.text,
            letterSpacing:"-0.02em",marginBottom:4}}>Business Rules</h2>
          <p style={{fontSize:13,color:T.secondary}}>
            {active} of {rules.length} active · loaded dynamically at runtime
          </p>
        </div>
        <div style={{display:"flex",gap:8}}>
          <button onClick={load} style={{background:T.surface,border:`1px solid ${T.border}`,
            color:T.secondary,padding:"8px 14px",borderRadius:8,cursor:"pointer",
            fontSize:13,fontWeight:500}}>↻ Refresh</button>
          {perms.rules
            ?<button onClick={()=>setShowCreate(true)}
                style={{background:T.accent,border:"none",color:"white",
                  padding:"8px 16px",borderRadius:8,cursor:"pointer",fontSize:13,
                  fontWeight:600,boxShadow:"0 2px 8px rgba(0,113,227,0.3)"}}>
                + Create Rule
              </button>
            :<LockedBtn label="Create Rule" reason="Requires Admin role"/>}
        </div>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
        {rules.map(r=>(
          <div key={r.rule_id}
            style={{background:T.card,borderRadius:14,padding:"16px 18px",
              boxShadow:T.shadow,opacity:r.enabled?1:0.52,transition:"all 0.2s"}}>
            <div style={{display:"flex",justifyContent:"space-between",
              alignItems:"flex-start",marginBottom:12}}>
              <div style={{flex:1,marginRight:14}}>
                <div style={{fontSize:14,fontWeight:600,color:T.text,marginBottom:3,
                  letterSpacing:"-0.01em"}}>
                  {r.name?.replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase())}
                </div>
                <div style={{fontSize:12,color:T.secondary,lineHeight:1.5}}>{r.description}</div>
              </div>
              {/* Toggle */}
              <div onClick={()=>toggle(r)}
                style={{width:40,height:22,borderRadius:11,flexShrink:0,
                  background:r.enabled?T.green:"#E5E5EA",position:"relative",
                  transition:"background 0.2s",
                  cursor:perms.rules?"pointer":"not-allowed",
                  title:perms.rules?"":"Requires Admin role"}}>
                {toggling===r.rule_id
                  ?<div style={{position:"absolute",top:"50%",left:"50%",
                      transform:"translate(-50%,-50%)",scale:"0.65"}}><Spin/></div>
                  :<div style={{position:"absolute",top:2,left:r.enabled?19:2,
                      width:16,height:16,borderRadius:"50%",background:"white",
                      transition:"left 0.2s",boxShadow:"0 1px 4px rgba(0,0,0,0.25)"}}/>}
                {!perms.rules&&<div style={{position:"absolute",inset:0,borderRadius:11,
                  display:"flex",alignItems:"center",justifyContent:"center",
                  fontSize:9,color:"white",background:"rgba(0,0,0,0.15)"}}>🔒</div>}
              </div>
            </div>

            <div style={{display:"flex",flexWrap:"wrap",gap:6}}>
              {r.override?.impact&&(
                <span style={{background:IMPACT[r.override.impact]?.bg||T.surface,
                  color:IMPACT[r.override.impact]?.c||T.secondary,
                  padding:"2px 8px",borderRadius:20,fontSize:11,fontWeight:500}}>
                  → {r.override.impact} impact
                </span>
              )}
              {r.override?.force_route&&(
                <span style={{background:T.redLight,color:T.red,
                  padding:"2px 8px",borderRadius:20,fontSize:11,fontWeight:500}}>⛔ hard block</span>
              )}
              {r.override?.reversibility&&(
                <span style={{background:T.orangeLight,color:T.orange,
                  padding:"2px 8px",borderRadius:20,fontSize:11,fontWeight:500}}>
                  → {r.override.reversibility}
                </span>
              )}
              {r.override?.add_approvers?.map(a=>(
                <span key={a} style={{background:T.purpleLight,color:T.purple,
                  padding:"2px 8px",borderRadius:20,fontSize:11,fontWeight:500}}>+ {a}</span>
              ))}
              <span style={{background:T.accentLight,color:T.accent,
                padding:"2px 8px",borderRadius:20,fontSize:11,fontWeight:600,marginLeft:"auto",
                fontVariantNumeric:"tabular-nums"}}>⚡ {r.fired_count||0}×</span>
            </div>
          </div>
        ))}
      </div>

      {showCreate&&(
        <CreateRuleModal api={api}
          onClose={()=>setShowCreate(false)}
          onDone={()=>setRefreshKey(k=>k+1)}/>
      )}
    </div>
  );
}

const CHART_COLORS=[T.accent,"#34C759","#FF9F0A","#FF3B30","#BF5AF2","#FF6B35","#AEAEB2"];
const tipStyle={contentStyle:{background:T.card,border:`1px solid ${T.border}`,
  borderRadius:10,color:T.text,fontSize:11,boxShadow:T.shadowMd}};

function AnalyticsPage({api,perms}) {
  const [stats,setStats]         = useState(null);
  const [decisions,setDecisions] = useState([]);
  const [loading,setLoading]     = useState(true);

  useEffect(()=>{
    if(!perms.stats){setLoading(false);return;}
    Promise.all([api("/decisions/stats/summary"),api("/decisions/")])
      .then(([s,d])=>{setStats(s);setDecisions(d.decisions||[]);})
      .catch(console.error).finally(()=>setLoading(false));
  },[api,perms]);

  if(!perms.stats)return(
    <div style={{textAlign:"center",padding:"80px 0",animation:"fadeIn 0.2s ease"}}>
      <div style={{fontSize:32,marginBottom:12,opacity:0.3}}>🔒</div>
      <div style={{fontSize:18,fontWeight:600,color:T.text,marginBottom:8}}>Admin Only</div>
      <div style={{color:T.secondary,fontSize:14}}>Analytics are only visible to Admin role</div>
    </div>
  );
  if(loading)return<div style={{display:"flex",justifyContent:"center",padding:80}}><Spin/></div>;

  const statusData=stats?Object.entries(stats).filter(([,v])=>v>0)
    .map(([k,v])=>({name:STATUS[k]?.label||k,value:v,color:STATUS[k]?.c||"#AEAEB2"})):[];
  const impactData=["low","medium","high","critical"].map(i=>({
    name:i.charAt(0).toUpperCase()+i.slice(1),
    count:decisions.filter(d=>d.classification?.impact===i).length,
    color:IMPACT[i]?.c,
  })).filter(d=>d.count>0);
  const agentCounts=decisions.reduce((a,d)=>{
    const n=fmt.agent(d.agent_id);a[n]=(a[n]||0)+1;return a;
  },{});
  const topAgents=Object.entries(agentCounts).sort((a,b)=>b[1]-a[1]).slice(0,6)
    .map(([name,count])=>({name,count}));

  const total=decisions.length;
  const completed=decisions.filter(d=>d.status==="completed").length;
  const rolledBack=decisions.filter(d=>d.status==="rolled_back").length;
  const rejected=decisions.filter(d=>d.status==="rejected").length;
  const card={background:T.card,borderRadius:16,padding:"18px 20px",boxShadow:T.shadow};
  const sL={fontSize:10,color:T.secondary,marginBottom:14,
    textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:600};

  return(
    <div style={{animation:"fadeIn 0.2s ease"}}>
      <h2 style={{fontSize:20,fontWeight:700,color:T.text,letterSpacing:"-0.02em",marginBottom:20}}>Analytics</h2>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:16}}>
        <StatCard label="Total"       value={total}     color={T.accent}  accent={T.accent}/>
        <StatCard label="Completed"   value={completed} color={T.green}   accent={T.green}
          sub={total?`${Math.round(completed/total*100)}% success`:""}/>
        <StatCard label="Rolled Back" value={rolledBack} color={T.orange} accent={T.orange}/>
        <StatCard label="Rejected"    value={rejected}  color={T.red}     accent={T.red}/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:12}}>
        <div style={card}>
          <div style={sL}>Status Breakdown</div>
          {statusData.length
            ?<ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={statusData} cx="50%" cy="50%" outerRadius={65} dataKey="value"
                    label={({name,percent})=>`${name} ${(percent*100).toFixed(0)}%`}
                    labelLine={false} fontSize={10}>
                    {statusData.map((e,i)=><Cell key={i} fill={e.color}/>)}
                  </Pie>
                  <Tooltip {...tipStyle}/>
                </PieChart>
              </ResponsiveContainer>
            :<Empty msg="No data yet"/>}
        </div>
        <div style={card}>
          <div style={sL}>Impact Distribution</div>
          {impactData.length
            ?<ResponsiveContainer width="100%" height={180}>
                <BarChart data={impactData} barSize={28}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.borderLight} vertical={false}/>
                  <XAxis dataKey="name" tick={{fill:T.secondary,fontSize:10}} axisLine={false} tickLine={false}/>
                  <YAxis tick={{fill:T.secondary,fontSize:10}} axisLine={false} tickLine={false}/>
                  <Tooltip {...tipStyle}/>
                  <Bar dataKey="count" radius={[5,5,0,0]}>
                    {impactData.map((e,i)=><Cell key={i} fill={e.color}/>)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            :<Empty msg="No data yet"/>}
        </div>
      </div>
      <div style={card}>
        <div style={sL}>Top Agents by Volume</div>
        {topAgents.length?topAgents.map((a,i)=>(
          <div key={a.name} style={{display:"flex",justifyContent:"space-between",
            alignItems:"center",padding:"9px 0",
            borderBottom:i<topAgents.length-1?`1px solid ${T.borderLight}`:"none"}}>
            <span style={{fontSize:13,color:T.text,fontWeight:500}}>{a.name}</span>
            <div style={{display:"flex",alignItems:"center",gap:12}}>
              <div style={{width:120,height:4,background:T.borderLight,borderRadius:2}}>
                <div style={{width:`${(a.count/topAgents[0].count)*100}%`,height:"100%",
                  background:CHART_COLORS[i%CHART_COLORS.length],borderRadius:2}}/>
              </div>
              <span style={{color:T.accent,fontSize:13,fontWeight:600,
                fontVariantNumeric:"tabular-nums",minWidth:18,textAlign:"right"}}>{a.count}</span>
            </div>
          </div>
        )):<Empty msg="No decisions yet"/>}
      </div>
    </div>
  );
}

function AdminPage({api,perms}) {
  const [ttlLoading,setTtlLoading] = useState(false);
  const [ttlMsg,setTtlMsg]         = useState("");
  const history = getHistory();

  const expireTTL = async()=>{
    setTtlLoading(true);setTtlMsg("");
    try{
      await api("/decisions/ttl/expire",{method:"POST"});
      setTtlMsg("TTL expiry check completed. Stale pending decisions rejected.");
    }catch(e){setTtlMsg(`Error: ${e.message}`);}
    setTtlLoading(false);
  };

  if(!perms.adminPanel)return(
    <div style={{textAlign:"center",padding:"80px 0",animation:"fadeIn 0.2s ease"}}>
      <div style={{fontSize:32,marginBottom:12,opacity:0.3}}>🔒</div>
      <div style={{fontSize:18,fontWeight:600,color:T.text,marginBottom:8}}>Admin Only</div>
      <div style={{color:T.secondary,fontSize:14}}>Admin panel requires Admin role</div>
    </div>
  );

  const roleBadge = r => {
    const u=Object.values(USERS).find(x=>x.role===r);
    return<span style={{background:`${u?.color||T.accent}18`,color:u?.color||T.accent,
      padding:"2px 10px",borderRadius:20,fontSize:11,fontWeight:600}}>{r}</span>;
  };

  return(
    <div style={{animation:"fadeIn 0.2s ease"}}>
      <h2 style={{fontSize:20,fontWeight:700,color:T.text,
        letterSpacing:"-0.02em",marginBottom:6}}>Admin Panel</h2>
      <p style={{fontSize:13,color:T.secondary,marginBottom:22}}>
        System maintenance and session history
      </p>

      {/* Maintenance */}
      <div style={{background:T.card,borderRadius:16,padding:"20px 22px",
        boxShadow:T.shadow,marginBottom:16}}>
        <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:4}}>
          TTL Expiry Monitor
        </div>
        <div style={{fontSize:12,color:T.secondary,marginBottom:14,lineHeight:1.5}}>
          Manually trigger the TTL check. Any pending decisions past their expiry time
          will be automatically rejected. This runs automatically every 60 seconds.
        </div>
        {ttlMsg&&<div style={{marginBottom:12,padding:"9px 12px",
          background:ttlMsg.startsWith("Error")?T.redLight:T.greenLight,
          borderRadius:8,fontSize:12,
          color:ttlMsg.startsWith("Error")?T.red:T.green}}>{ttlMsg}</div>}
        <button onClick={expireTTL} disabled={ttlLoading}
          style={{background:T.surface,border:`1px solid ${T.border}`,color:T.text,
            padding:"9px 18px",borderRadius:8,cursor:ttlLoading?"not-allowed":"pointer",
            fontSize:13,fontWeight:500,display:"flex",alignItems:"center",gap:8}}>
          {ttlLoading?<><Spin/>Running…</>:"⏱ Run TTL Expiry Check"}
        </button>
      </div>

      {/* Users */}
      <div style={{background:T.card,borderRadius:16,padding:"20px 22px",
        boxShadow:T.shadow,marginBottom:16}}>
        <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:14}}>
          System Users
        </div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:10}}>
          {Object.entries(USERS).map(([username,u])=>(
            <div key={username} style={{background:T.surface,borderRadius:10,
              padding:"14px 16px",border:`1px solid ${T.border}`}}>
              <div style={{fontSize:14,fontWeight:600,color:T.text,marginBottom:4}}>
                {username}
              </div>
              <div style={{marginBottom:6}}>{roleBadge(u.role)}</div>
              <div style={{fontSize:11,color:T.secondary}}>
                {u.role==="admin"?"Full access — all operations"
                  :u.role==="approver"?"Can approve, reject, execute"
                  :"Can submit and read decisions"}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Session history */}
      <div style={{background:T.card,borderRadius:16,boxShadow:T.shadow,overflow:"hidden"}}>
        <div style={{padding:"14px 20px",borderBottom:`1px solid ${T.border}`}}>
          <div style={{fontSize:13,fontWeight:600,color:T.text}}>
            Session History ({history.length})
          </div>
          <div style={{fontSize:11,color:T.secondary,marginTop:2}}>
            Stored in browser localStorage
          </div>
        </div>
        {history.length===0
          ?<Empty msg="No session history yet"/>
          :history.slice(0,20).map((s,i)=>(
            <div key={i} style={{display:"flex",justifyContent:"space-between",
              alignItems:"center",padding:"11px 20px",
              borderBottom:i<Math.min(history.length,20)-1?`1px solid ${T.borderLight}`:"none"}}>
              <div style={{display:"flex",alignItems:"center",gap:10}}>
                <div style={{width:28,height:28,borderRadius:"50%",
                  background:`${USERS[s.username]?.color||T.accent}18`,
                  display:"flex",alignItems:"center",justifyContent:"center",
                  fontSize:12,fontWeight:700,color:USERS[s.username]?.color||T.accent}}>
                  {s.username[0].toUpperCase()}
                </div>
                <div>
                  <div style={{fontSize:13,fontWeight:500,color:T.text}}>{s.username}</div>
                  <div style={{fontSize:11,color:T.secondary}}>{s.role}</div>
                </div>
              </div>
              <div style={{fontSize:12,color:T.tertiary,fontVariantNumeric:"tabular-nums"}}>
                {fmt.dt(s.loginAt)}
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}

// ─── Login Page ─────────────────────────────────────────────────
function LoginPage({onLogin}) {
  const [username,setUsername] = useState("");
  const [password,setPassword] = useState("");
  const [err,setErr]           = useState("");
  const [loading,setLoading]   = useState(false);

  const login = async()=>{
    setErr("");setLoading(true);
    await new Promise(r=>setTimeout(r,400)); // subtle delay for feel
    const user=USERS[username.toLowerCase()];
    if(!user||user.password!==password){
      setErr("Invalid username or password");setLoading(false);return;
    }
    saveSession(username.toLowerCase(),user.role);
    onLogin({username:username.toLowerCase(),role:user.role});
    setLoading(false);
  };

  const handleKey = e=>{if(e.key==="Enter")login();};

  return(
    <div style={{minHeight:"100vh",background:T.surface,display:"flex",
      alignItems:"center",justifyContent:"center",animation:"fadeIn 0.3s ease"}}>
      <div style={{width:380,animation:"fadeIn 0.4s ease"}}>
        {/* Logo */}
        <div style={{textAlign:"center",marginBottom:32}}>
          <div style={{width:60,height:60,borderRadius:16,background:T.accent,
            display:"flex",alignItems:"center",justifyContent:"center",
            margin:"0 auto 16px",boxShadow:"0 8px 24px rgba(0,113,227,0.35)"}}>
            <span style={{fontSize:24,color:"white",fontWeight:700}}>A</span>
          </div>
          <div style={{fontSize:24,fontWeight:700,color:T.text,
            letterSpacing:"-0.03em",marginBottom:4}}>ARIA</div>
          <div style={{fontSize:13,color:T.secondary}}>
            AI Reliability & Integrity Architecture
          </div>
        </div>

        {/* Card */}
        <div style={{background:T.bg,borderRadius:20,padding:"32px 28px",
          boxShadow:T.shadowLg}}>
          <div style={{fontSize:18,fontWeight:700,color:T.text,
            letterSpacing:"-0.02em",marginBottom:4}}>Sign in</div>
          <div style={{fontSize:13,color:T.secondary,marginBottom:22}}>
            Use your assigned credentials to continue
          </div>

          {err&&<div style={{marginBottom:14,padding:"10px 14px",background:T.redLight,
            borderRadius:8,fontSize:13,color:T.red}}>{err}</div>}

          <div style={{marginBottom:14}}>
            <div style={{fontSize:12,color:T.secondary,marginBottom:5,fontWeight:500}}>
              Username
            </div>
            <input value={username} onChange={e=>setUsername(e.target.value)}
              onKeyDown={handleKey} placeholder="admin / approver / tester"
              autoComplete="username"
              style={{...IS,fontSize:14}}/>
          </div>

          <div style={{marginBottom:20}}>
            <div style={{fontSize:12,color:T.secondary,marginBottom:5,fontWeight:500}}>
              Password
            </div>
            <input value={password} onChange={e=>setPassword(e.target.value)}
              onKeyDown={handleKey} type="password" placeholder="••••••••••••••"
              autoComplete="current-password"
              style={{...IS,fontSize:14}}/>
          </div>

          <button onClick={login} disabled={loading}
            style={{width:"100%",background:T.accent,border:"none",color:"white",
              padding:"13px",borderRadius:10,fontSize:14,fontWeight:600,
              cursor:loading?"not-allowed":"pointer",opacity:loading?0.7:1,
              boxShadow:"0 4px 12px rgba(0,113,227,0.35)",letterSpacing:"0.01em"}}>
            {loading?"Signing in…":"Sign In →"}
          </button>

          {/* Hint */}
          <div style={{marginTop:20,padding:"12px 14px",background:T.surface,
            borderRadius:10,border:`1px solid ${T.border}`}}>
            <div style={{fontSize:11,color:T.secondary,marginBottom:6,fontWeight:500}}>
              Demo credentials
            </div>
            {[["admin","aria-admin-2026","#0071E3"],
              ["approver","aria-approver-2026","#34C759"],
              ["tester","aria-tester-2026","#FF9F0A"]].map(([u,p,c])=>(
              <div key={u} style={{display:"flex",justifyContent:"space-between",
                alignItems:"center",marginBottom:3}}>
                <span style={{fontSize:11,color:c,fontWeight:600}}>{u}</span>
                <span style={{fontSize:10,color:T.tertiary,
                  fontFamily:"'SF Mono',monospace"}}>{p}</span>
              </div>
            ))}
          </div>
        </div>
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
  {id:"admin",     label:"Admin",     icon:"⚙", adminOnly:true},
];

// ─── App Shell ───────────────────────────────────────────────────
export default function App() {
  const [user,setUser]     = useState(()=>getSession());
  const [page,setPage]     = useState("overview");
  const [jumpId,setJumpId] = useState(null);
  const [showRolePicker,setShowRolePicker] = useState(false);

  const perms = PERMS[user?.role] || PERMS.tester;
  const userData = user ? USERS[user.username] : null;
  const apiKey = userData?.apiKey || "";
  const api = useApi(apiKey);

  const logout = ()=>{clearSession();setUser(null);setPage("overview");};

  const switchRole = (username)=>{
    const u=USERS[username];
    if(!u)return;
    saveSession(username,u.role);
    setUser({username,role:u.role});
    setShowRolePicker(false);
  };

  const handleSelectDecision = id=>{setJumpId(id);setPage("decisions");};

  if(!user)return<><style>{css}</style><LoginPage onLogin={u=>{setUser(u);}}/></>;

  const visibleNav=NAV.filter(n=>!n.adminOnly||perms.adminPanel);

  return(
    <div style={{display:"flex",height:"100vh",background:T.surface,
      fontFamily:"-apple-system,BlinkMacSystemFont,'Inter',Helvetica,Arial,sans-serif",
      color:T.text,overflow:"hidden"}}>
      <style>{css}</style>

      {/* Sidebar */}
      <div style={{width:196,background:T.bg,borderRight:`1px solid ${T.border}`,
        display:"flex",flexDirection:"column",flexShrink:0}}>
        <div style={{padding:"22px 18px 18px"}}>
          <div style={{fontSize:19,fontWeight:700,color:T.text,letterSpacing:"-0.03em"}}>ARIA</div>
          <div style={{fontSize:9,color:T.tertiary,marginTop:1,
            letterSpacing:"0.12em",textTransform:"uppercase",fontWeight:500}}>Control Center</div>
        </div>
        <Divider/>
        <nav style={{flex:1,padding:"10px 8px"}}>
          {visibleNav.map(n=>(
            <button key={n.id} onClick={()=>setPage(n.id)}
              style={{display:"flex",alignItems:"center",gap:9,width:"100%",
                padding:"9px 11px",borderRadius:8,border:"none",cursor:"pointer",
                background:page===n.id?T.accentLight:"transparent",
                color:page===n.id?T.accent:T.secondary,
                fontSize:13,fontWeight:page===n.id?600:400,
                marginBottom:2,transition:"all 0.14s",textAlign:"left"}}>
              <span style={{fontSize:13,opacity:page===n.id?1:0.65}}>{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>
        <Divider/>
        {/* User info */}
        <div style={{padding:"12px 10px"}}>
          <div style={{display:"flex",alignItems:"center",gap:8,
            padding:"8px 10px",borderRadius:8,marginBottom:4}}>
            <div style={{width:28,height:28,borderRadius:"50%",
              background:`${userData?.color||T.accent}18`,flexShrink:0,
              display:"flex",alignItems:"center",justifyContent:"center",
              fontSize:12,fontWeight:700,color:userData?.color||T.accent}}>
              {user.username[0].toUpperCase()}
            </div>
            <div style={{flex:1,minWidth:0}}>
              <div style={{fontSize:12,fontWeight:600,color:T.text,
                overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                {user.username}
              </div>
              <div style={{fontSize:10,color:T.secondary}}>{user.role}</div>
            </div>
          </div>
          <button onClick={logout}
            style={{width:"100%",background:"none",border:`1px solid ${T.border}`,
              color:T.secondary,padding:"7px",borderRadius:7,cursor:"pointer",
              fontSize:12,fontWeight:500}}>Sign Out</button>
        </div>
      </div>

      {/* Main */}
      <div style={{flex:1,display:"flex",flexDirection:"column",minWidth:0,overflow:"hidden"}}>

        {/* Header */}
        <div style={{padding:"13px 26px",borderBottom:`1px solid ${T.border}`,
          display:"flex",justifyContent:"space-between",alignItems:"center",
          background:T.bg,flexShrink:0}}>
          <div>
            <div style={{fontSize:15,fontWeight:700,color:T.text,letterSpacing:"-0.02em"}}>
              {NAV.find(n=>n.id===page)?.label}
            </div>
            <div style={{fontSize:11,color:T.tertiary,marginTop:1}}>
              AI Reliability & Integrity Architecture
            </div>
          </div>
          <div style={{display:"flex",gap:8,alignItems:"center",position:"relative"}}>

            {/* Role switcher */}
            <button onClick={()=>setShowRolePicker(p=>!p)}
              style={{display:"flex",alignItems:"center",gap:6,
                background:T.surface,border:`1px solid ${T.border}`,
                color:T.text,padding:"7px 12px",borderRadius:8,
                cursor:"pointer",fontSize:12,fontWeight:500}}>
              <span style={{width:8,height:8,borderRadius:"50%",flexShrink:0,
                background:userData?.color||T.accent,display:"inline-block"}}/>
              {userData?.displayName} ▾
            </button>

            {showRolePicker&&(
              <>
                <div style={{position:"fixed",inset:0,zIndex:49}}
                  onClick={()=>setShowRolePicker(false)}/>
                <div style={{position:"absolute",top:"calc(100% + 6px)",right:0,
                  background:T.bg,border:`1px solid ${T.border}`,borderRadius:12,
                  boxShadow:T.shadowMd,padding:"6px",zIndex:50,minWidth:200,
                  animation:"fadeIn 0.15s ease"}}>
                  <div style={{fontSize:10,color:T.tertiary,padding:"6px 10px 4px",
                    textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:500}}>
                    Switch Role
                  </div>
                  {Object.entries(USERS).map(([u,data])=>(
                    <button key={u} onClick={()=>switchRole(u)}
                      style={{display:"flex",alignItems:"center",gap:10,width:"100%",
                        padding:"9px 10px",borderRadius:8,border:"none",cursor:"pointer",
                        background:user.username===u?T.accentLight:"transparent",
                        textAlign:"left",transition:"background 0.12s"}}>
                      <div style={{width:26,height:26,borderRadius:"50%",
                        background:`${data.color}18`,flexShrink:0,
                        display:"flex",alignItems:"center",justifyContent:"center",
                        fontSize:11,fontWeight:700,color:data.color}}>
                        {u[0].toUpperCase()}
                      </div>
                      <div>
                        <div style={{fontSize:13,fontWeight:500,color:T.text}}>{u}</div>
                        <div style={{fontSize:10,color:T.secondary}}>{data.role}</div>
                      </div>
                      {user.username===u&&<span style={{marginLeft:"auto",color:T.accent,fontSize:12}}>✓</span>}
                    </button>
                  ))}
                </div>
              </>
            )}

            {CONFIG.url&&(
              <a href={`${CONFIG.url}/docs`} target="_blank" rel="noreferrer"
                style={{background:T.surface,border:`1px solid ${T.border}`,
                  color:T.secondary,padding:"7px 13px",borderRadius:8,
                  fontSize:12,fontWeight:500,display:"flex",alignItems:"center",gap:4}}>
                API ↗
              </a>
            )}
          </div>
        </div>

        {/* Page content */}
        <div style={{flex:1,overflowY:"auto",padding:"22px 26px"}}>
          {!CONFIG.url
            ?<div style={{textAlign:"center",padding:"80px 0"}}>
                <div style={{fontSize:32,marginBottom:12,opacity:0.25}}>◌</div>
                <div style={{fontSize:18,fontWeight:600,color:T.text,marginBottom:8}}>
                  API Not Configured
                </div>
                <div style={{color:T.secondary,fontSize:14}}>
                  Set VITE_API_URL in your .env file and rebuild
                </div>
              </div>
            :page==="overview"  ?<OverviewPage  api={api} perms={perms} onSelectDecision={handleSelectDecision}/>
            :page==="decisions" ?<DecisionsPage api={api} perms={perms} initialId={jumpId}/>
            :page==="rules"     ?<RulesPage     api={api} perms={perms}/>
            :page==="analytics" ?<AnalyticsPage api={api} perms={perms}/>
            :                    <AdminPage      api={api} perms={perms}/>
          }
        </div>
      </div>
    </div>
  );
}