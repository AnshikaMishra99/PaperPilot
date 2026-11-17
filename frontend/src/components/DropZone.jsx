import { useRef, useState } from 'react'

export default function DropZone({ onFiles, disabled, maxMb, maxFiles }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = (fileList) => {
    const files = Array.from(fileList || [])
    if (files.length) onFiles(files)
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault()
        if (!disabled) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        if (!disabled) handleFiles(event.dataTransfer.files)
      }}
      className={`rounded-lg border-2 border-dashed px-6 py-12 text-center ${
        dragging ? 'border-pine-500 bg-pine-50' : 'border-line bg-surface'
      } ${disabled ? 'opacity-60' : ''}`}
    >
      <p className="font-read text-lg text-ink">Drop PDFs here</p>
      <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted">
        Up to {maxFiles} papers at a time, {maxMb} MB each. Text-based PDFs only — a scan with no
        text layer has nothing to index.
      </p>

      <button
        type="button"
        className="btn-quiet mt-5"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        Choose files
      </button>

      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        className="hidden"
        onChange={(event) => {
          handleFiles(event.target.files)
          event.target.value = ''
        }}
      />
    </div>
  )
}
