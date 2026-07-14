import React, {useEffect, useState} from 'react'

export default function PreviewDemo() {
  const [payload, setPayload] = useState<any>(null)
  const [state, setState] = useState('Normal')

  useEffect(() => {
    // demo: fetch preview for a small hardcoded boards payload
    const body = {
      boards: [
        {id: 'a', title: 'Dashboard', elements: [{type: 'button', text: 'Open Alert Configuration'}]},
        {id: 'b', title: 'Alert Configuration', elements: []}
      ],
      state_definitions: {Normal: {overrides: {}}, Critical: {overrides: {}}}
    }
    fetch('/api/preview/', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
      .then(r => r.json())
      .then(setPayload)
      .catch(e => setPayload({error: String(e)}))
  }, [])

  if (!payload) return <div>Loading preview...</div>

  return (
    <div style={{padding: 16}}>
      <h3>Preview Demo</h3>
      <div style={{marginBottom: 8}}>
        <label>State: </label>
        <select value={state} onChange={e => setState(e.target.value)}>
          <option>Normal</option>
          <option>Critical</option>
        </select>
      </div>
      <div>
        <h4>Flows</h4>
        <pre>{JSON.stringify(payload.flows, null, 2)}</pre>
      </div>
      <div>
        <h4>Transformed Sample</h4>
        <pre>{JSON.stringify(payload.transformed_sample, null, 2)}</pre>
      </div>
    </div>
  )
}
