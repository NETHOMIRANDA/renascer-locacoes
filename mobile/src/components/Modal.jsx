import React from 'react'

export default function Modal({ title, onClose, children }) {
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h3>{title}</h3>
          <button className="btn sm ghost" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}