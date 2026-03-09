import type { ReactNode } from 'react'

export type Column<T> = {
  key: string
  header: ReactNode
  render: (row: T, rowIndex: number) => ReactNode
}

type Props<T> = {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  onRowClick?: (row: T) => void
}

export default function DataTable<T>({ columns, rows, rowKey, onRowClick }: Props<T>) {
  return (
    <div className='table-wrap'>
      <table className='table'>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className='table__th'>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => {
            const clickable = onRowClick !== undefined
            let rowClass = 'table__tr'
            if (clickable) {
              rowClass = 'table__tr table__tr--clickable'
            }
            return (
              <tr key={rowKey(row)} className={rowClass} onClick={() => onRowClick?.(row)}>
                {columns.map((col) => (
                  <td key={col.key} className='table__td'>
                    {col.render(row, rowIndex)}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
