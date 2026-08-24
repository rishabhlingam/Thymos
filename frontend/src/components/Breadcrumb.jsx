function Breadcrumb({ items }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500 mb-4 flex-wrap">
      {items.map((item, i) => (
        <span key={item.label} className="flex items-center gap-2">
          {i > 0 && <span className="text-slate-300">/</span>}
          <span>
            {item.label}:{' '}
            <span className="text-accent font-medium">{item.value}</span>
          </span>
        </span>
      ))}
    </div>
  )
}

export default Breadcrumb