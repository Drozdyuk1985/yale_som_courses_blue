import { useState } from 'react'
import type { Course } from '../api'

export function CourseCard({ course }: { course: Course }) {
  const [open, setOpen] = useState(false)
  const description = course.course_description?.trim() ?? ''
  const isLong = description.length > 220

  return (
    <article className="card">
      <header className="card-head">
        <span className="badge">{course.course_number}</span>
        {course.section && <span className="section">Sec {course.section}</span>}
      </header>

      <h3 className="card-title">{course.course_title}</h3>

      <dl className="meta">
        <div>
          <dt>Faculty</dt>
          <dd>{course.faculty || 'TBA'}</dd>
        </div>
        <div>
          <dt>Meets</dt>
          <dd>{course.daytimes || 'Schedule TBA'}</dd>
        </div>
        <div>
          <dt>Room</dt>
          <dd>{course.room || '—'}</dd>
        </div>
        <div>
          <dt>Units</dt>
          <dd>{course.units || '—'}</dd>
        </div>
      </dl>

      {description && (
        <p className={`desc ${open ? 'open' : ''}`}>
          {open || !isLong ? description : `${description.slice(0, 220)}…`}
        </p>
      )}

      <footer className="card-foot">
        <div className="chips">
          {course.course_category && <span className="chip">{course.course_category}</span>}
          {course.bid_or_permission && (
            <span className="chip chip-quiet">{course.bid_or_permission}</span>
          )}
        </div>
        {isLong && (
          <button className="link-btn" onClick={() => setOpen((v) => !v)}>
            {open ? 'Less' : 'More'}
          </button>
        )}
      </footer>
    </article>
  )
}
