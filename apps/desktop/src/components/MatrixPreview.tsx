import React, {useEffect, useRef, useState} from 'react'

export default function MatrixPreview({matrix}:{matrix: Record<string, any>}){
  const [diagnostics, setDiagnostics] = useState<Record<string, string[]>>({})
  const iframes = useRef<Record<string, HTMLIFrameElement | null>>({})

  // listen for messages from iframes (in-iframe diagnostics)
  useEffect(()=>{
    function handler(ev: MessageEvent){
      try{
        const data = ev.data
        if(!data || !data.__preview_diag) return
        const {vp, issues} = data
        setDiagnostics(prev => ({...prev, [vp]: issues}))
      }catch(e){/* ignore malformed */}
    }
    window.addEventListener('message', handler)
    return ()=> window.removeEventListener('message', handler)
  }, [])

  // build srcDoc for iframe from sample
  function buildSrcDoc(vp: string, sample: any){
    const elemsHtml = (sample.elements || []).map((e:any, idx:number)=>{
      const role = (e.type || e.__role || `el-${idx}`)
      if(e.type === 'button'){
        return `<button data-role="${role}" style="display:inline-block;padding:8px 12px;margin:6px 0;border-radius:6px;border:1px solid #ccc;background:#fff">${escapeHtml(e.text||'')}</button>`
      }
      if(e.type === 'metric' || role === 'metric'){
        return `<div data-role="${role}" style="font-size:20px;font-weight:700;margin:6px 0">${escapeHtml(e.text||'')}</div>`
      }
      // fallback block
      return `<div data-role="${role}" style="margin:6px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%">${escapeHtml(e.text||'')}</div>`
    }).join('\n')

    const script = `
      (function(){
        function escape(s){ return String(s) }
        function scan(){
          const issues = []
          const els = document.querySelectorAll('[data-role]')
          els.forEach(el=>{
            const rect = el.getBoundingClientRect()
            if(el.scrollWidth > el.clientWidth + 1){
              issues.push('Overflow in element: ' + (el.getAttribute('data-role') || el.innerText.slice(0,20)))
            }
            // detect long text without wrapping
            const text = el.textContent || ''
            if(text.length > 120){
              issues.push('Long text (truncation risk) in: ' + (el.getAttribute('data-role') || text.slice(0,20)))
            }
          })
          // send diagnostics to parent
          parent.postMessage({__preview_diag:true, vp: '${vp}', issues: issues}, '*')
        }
        // run after layout
        window.addEventListener('load', ()=> setTimeout(scan, 50))
        // also run on resize
        window.addEventListener('resize', ()=> setTimeout(scan, 50))
      })()
    `

    return `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=${vp},initial-scale=1" />
<style>body{font-family:Inter,system-ui,Segoe UI,Helvetica,Arial,sans-serif;padding:12px;margin:0;background:#fff;color:#111}*{box-sizing:border-box}</style>
</head>
<body>
<div id="root">${elemsHtml}</div>
<script>${script}</script>
</body>
</html>`
  }

  function escapeHtml(s:string){
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  }

  return (
    <div style={{display:'flex', gap:12}}>
      <div style={{flex:3, display:'flex', gap:12}}>
        {Object.entries(matrix).map(([vp, sample])=> (
          <div key={vp} style={{flex:1, border:'1px solid #e6e6e6', padding:8, borderRadius:8, background:'#fff'}}>
            <div style={{fontWeight:700, marginBottom:6}}>{vp}px viewport</div>
            <div style={{width:'100%', boxSizing:'border-box', display:'flex', justifyContent:'center'}}>
              <iframe
                title={`preview-${vp}`}
                ref={el=> iframes.current[vp]=el}
                srcDoc={buildSrcDoc(vp, sample)}
                style={{width: `${vp}px`, height: 500, border:'1px solid #ddd', borderRadius:6}}
                sandbox="allow-scripts"
              />
            </div>
          </div>
        ))}
      </div>
      <div style={{flex:1, minWidth:260}}>
        <div style={{fontWeight:700, marginBottom:8}}>Diagnostics</div>
        {Object.keys(matrix).length===0 ? <div>No matrix</div> : (
          Object.entries(matrix).map(([vp, _sample])=> (
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
