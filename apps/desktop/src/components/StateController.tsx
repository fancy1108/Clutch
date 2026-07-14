import React from 'react'

export default function StateController({state, setState}:{state:string,setState:(s:string)=>void}){
  return (
    <div style={{display:'inline-block', marginRight: 12}}>
      <label style={{marginRight:8}}>Prototype State:</label>
      <button onClick={()=>setState('Normal')} style={{marginRight:6}}>🟢 Normal</button>
      <button onClick={()=>setState('Warning')} style={{marginRight:6}}>🟡 Warning</button>
      <button onClick={()=>setState('Critical')} style={{marginRight:6}}>🔴 Critical</button>
      <button onClick={()=>setState('DataOverflow')} style={{marginRight:6}}>🟣 Data Overflow</button>
    </div>
  )
}
