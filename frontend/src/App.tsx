import { useCallback, useEffect, useMemo, useState } from 'react'
import { clearSession, fetchCourses, getUsername, type Course } from './api'
import { CourseCard } from './components/CourseCard'
import { ChatPanel } from './components/ChatPanel'
import { MoneyTicker } from './components/MoneyTicker'
import { AuthScreen } from './components/AuthScreen'
import './App.css'

export default function App() {
  const [username, setUsername] = useState<string | null>(getUsername())
  const [courses, setCourses] = useState<Course[]>([])
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const signOut = useCallback(() => {
    clearSession()
    setUsername(null)
  }, [])

  useEffect(() => {
    if (!username) return
    let cancelled = false
    const timer = setTimeout(() => {
      setLoading(true)
      fetchCourses(search.trim() || undefined)
        .then((data) => {
          if (cancelled) return
          setCourses(data.courses)
          setError('')
        })
        .catch((e: Error) => !cancelled && setError(e.message))
        .finally(() => !cancelled && setLoading(false))
    }, 250)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [search, username])

  const categories = useMemo(() => {
    const found = new Set(courses.map((c) => c.course_category).filter(Boolean))
    return ['All', ...Array.from(found).sort()]
  }, [courses])

  const shown = useMemo(
    () => (category === 'All' ? courses : courses.filter((c) => c.course_category === category)),
    [courses, category],
  )

  if (!username) {
    return <AuthScreen onSignedIn={setUsername} />
  }

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-inner">
          <div>
            <p className="eyebrow">Yale School of Management</p>
            <h1>Course Explorer</h1>
          </div>
          <div className="user-box">
            <span className="term">Spring 2026</span>
            <span className="whoami">{username}</span>
            <button className="link-btn" onClick={signOut}>Sign out</button>
          </div>
        </div>
        <MoneyTicker />
      </header>

      <main className="layout">
        <section className="catalog">
          <div className="controls">
            <input
              className="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title, faculty, number, or keyword…"
            />
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <p className="count">
            {loading ? 'Loading…' : `${shown.length} course${shown.length === 1 ? '' : 's'}`}
          </p>

          {error && <p className="error">{error} — is the backend running on port 8000?</p>}

          <div className="grid">
            {shown.map((course, index) => (
              <CourseCard key={`${course.course_id}-${course.section}-${index}`} course={course} />
            ))}
          </div>

          {!loading && !error && shown.length === 0 && (
            <p className="empty-state">No courses match that search.</p>
          )}
        </section>

        <aside className="sidebar">
          <ChatPanel onSessionExpired={signOut} />
        </aside>
      </main>
    </div>
  )
}
