import React, {useEffect, useRef, useState} from 'react'

export default function MatrixPreview({matrix}:{matrix: Record<string, any>}){
  const [diagnostics, setDiagnostics] = useState<Record<string, string[]>>({})
  const refs = useRef<Record<string, HTMLDivElement | null>>({})

  useEffect(()=>{
    const diag: Record<string, string[]> = {}
    for(const vp of Object.keys(matrix)){
      const container = refs.current[vp]
      const msgs: string[] = []
      if(container){
        const elements = container.querySelectorAll<HTMLElement>('[data-role]')
        elements.forEach((el)=>{
          if(el.scrollWidth > el.clientWidth){
            msgs.push(`Overflow detected in element: ${el.dataset.role || el.innerText.slice(0,20)}`)
          }
        })
      }
      if(msgs.length) diag[vp] = msgs
    }
    setDiagnostics(diag)
  }, [matrix])

  return (
    <div style={{display:'flex', gap:12}}>
      <div style={{flex:3, display:'flex', gap:12}}>
        {Object.entries(matrix).map(([vp, sample])=> (
          <div key={vp} style={{flex:1, border:'1px solid #e6e6e6', padding:8, borderRadius:8, background:'#fff'}}>
            <div style={{fontWeight:700, marginBottom:6}}>{vp}px viewport</div>
            <div ref={el=> refs.current[vp]=el} style={{width: '100%', boxSizing:'border-box'}}>
              {sample.elements && sample.elements.map((e:any, idx:number)=>{
                const role = e.type || e.__role || `el-${idx}`
                if(e.type === 'button'){
                  return <button key={idx} data-role={role} style={{display:'inline-block', padding:'8px 12px', margin:'6px 0', borderRadius:6, border:'1px solid #ccc'}}>{e.text}</button>
                }
                if(e.type === 'metric' || role === 'metric'){
                  return <div key={idx} data-role={role} style={{fontSize:20, fontWeight:700, margin:'6px 0'}}>{e.text}</div>
                }
                // fallback text block
                return <div key={idx} data-role={role} style={{margin:'6px 0', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', maxWidth:'100%'}}>{e.text}</div>
              })}
            </div>
          </div>
        ))}
      </div>
      <div style={{flex:1, minWidth:260}}>
        <div style={{fontWeight:700, marginBottom:8}}>Diagnostics</div>
        {Object.keys(matrix).length===0 ? <div>No matrix</div> : (
          Object.entries(matrix).map(([vp, msgs])=> (
            <div key={vp} style={{marginBottom:12}}>
              <div style={{fontWeight:600}}>{vp}px</div>
              {diagnostics[vp] && diagnostics[vp].length ? (
                <ul>
                  {diagnostics[vp].map((m,i)=>(<li key={i} style={{color:'crimson'}}>{m}</li>))}
                </ul>
              ) : (<div style={{color:'green'}}>No issues detected</div>)}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
