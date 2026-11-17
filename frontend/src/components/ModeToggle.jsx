const options = [
  { value: 'simple', label: 'Plain language', hint: 'Explains terms as it goes' },
  { value: 'technical', label: 'Technical', hint: "Keeps the paper's terminology" },
]

export default function ModeToggle({ mode, onChange }) {
  return (
    <div className="inline-flex rounded-md border border-line bg-surface p-0.5">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          title={option.hint}
          onClick={() => onChange(option.value)}
          aria-pressed={mode === option.value}
          className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
            mode === option.value ? 'bg-pine-600 text-white' : 'text-muted hover:text-ink'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
