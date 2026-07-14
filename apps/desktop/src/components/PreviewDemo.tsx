import React, {useEffect, useState} from 'react'
import StateController from './StateController'
import MatrixPreview from './MatrixPreview'

export default function PreviewDemo() {
  const [payload, setPayload] = useState<any>(null)
  const [state, setState] = useState('Normal')

  const [extreme, setExtreme] = useState(false)
  const [viewports, setViewports] = useState(['2560','1440','390'])

  useEffect(() => {
    // demo: fetch preview for a small hardcoded boards payload
    const body = {
      boards: [
        {id: 'a', title: 'Dashboard', elements: [{type: 'button', text: 'Open Alert Configuration'}]},
        {id: 'b', title: 'Alert Configuration', elements: []}
      ],
      state_definitions: {Normal: {overrides: {}}, Critical: {overrides: {}}},
      preview_options: {extreme: extreme, viewports: viewports}
    }
    fetch('/api/preview/', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
      .then(r => r.json())
      .then(setPayload)
      .catch(e => setPayload({error: String(e)}))
  }, [extreme, viewports])

  if (!payload) return <div>Loading preview...</div>

  return (
    <div style={{padding: 16}}>
      <h3>Preview Demo</h3>
      <div style={{marginBottom: 8}}>
        <StateController state={state} setState={setState} />
        <label style={{marginLeft:12}}>
          <input type="checkbox" checked={extreme} onChange={e=>setExtreme(e.target.checked)} /> Extreme Mode
        </label>
      </div>

      <div style={{display:'flex', gap:12}}>
        {payload.matrix ? (
          importMetaNotUsed(),
          <MatrixPreview matrix={payload.matrix} />
        ) : (
          <div style={{flex:1}}>
            <h4>Transformed Sample</h4>
            <pre>{JSON.stringify(payload.transformed_sample, null, 2)}</pre>
          </div>
        )}
      </div>

      {payload.extreme_sample ? (
        <div style={{marginTop:12}}>
          <h4>Extreme Sample</h4>
          <pre style={{maxHeight:200,overflow:'auto'}}>{JSON.stringify(payload.extreme_sample, null, 2)}</pre>
        </div>
      ) : null}

      <div style={{marginTop:12}}>
        <h4>Flows</h4>
        <pre>{JSON.stringify(payload.flows, null, 2)}</pre>
      </div>
    </div>
  )
}

