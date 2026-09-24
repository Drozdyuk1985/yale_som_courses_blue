import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { clearHistory, fetchHistory, sendChat } from '../api'

type Turn = { role: 'user' | 'agent'; text: string; tools?: string[] }

export function ChatPanel({ onSessionExpired }: { onSessionExpired: () => void }) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchHistory()
      .then((data) => {
        setTurns(data.messages.map((m) => ({
          role: m.role,
          text: m.content,
          tools: m.tools_used,
        })))
      })
      .catch((e: Error) => {
        if (e.message.includes('session')) onSessionExpired()
      })
      .finally(() => setLoading(false))
  }, [onSessionExpired])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [turns, busy])

  const ask = async (event: React.FormEvent) => {
    event.preventDefault()
    const message = draft.trim()
    if (!message || busy) return

    setTurns((t) => [...t, { role: 'user', text: message }])
    setDraft('')
    setBusy(true)
    try {
      const data = await sendChat(message)
      setTurns((t) => [...t, { role: 'agent', text: data.reply, tools: data.tools_used }])
    } catch (e) {
      const msg = (e as Error).message
      if (msg.includes('session')) {
        onSessionExpired()
        return
      }
      setTurns((t) => [...t, { role: 'agent', text: `Could not reach the agent. ${msg}` }])
    } finally {
      setBusy(false)
    }
  }

  const wipe = async () => {
    if (!confirm('Delete your saved chat history? This cannot be undone.')) return
    try {
      await clearHistory()
      setTurns([])
    } catch (e) {
      alert((e as Error).message)
    }
  }

  return (
    <section className="chat">
      <header className="chat-head">
        <div className="chat-head-row">
          <h2>Ask the catalog</h2>
          {turns.length > 0 && (
            <button className="link-btn tiny" onClick={wipe}>Clear</button>
          )}
        </div>
        <p>Your conversation is saved to your account.</p>
      </header>

      <div className="chat-log" ref={logRef}>
        {loading && <div className="empty">Loading your history…</div>}

        {!loading && turns.length === 0 && !busy && (
          <div className="empty">
            <p>Try one of these:</p>
            <ul>
              <li>Which courses meet on Tuesdays?</li>
              <li>What does Erin Frey teach?</li>
              <li>Show me the finance electives.</li>
            </ul>
          </div>
        )}

        {turns.map((turn, index) => (
          <div key={index} className={`turn ${turn.role}`}>
            <div className="bubble">
              {turn.role === 'agent' ? (
                <div className="markdown">
                  <ReactMarkdown
                    components={{
                      a: ({ ...props }) => (
                        <a {...props} target="_blank" rel="noreferrer noopener" />
                      ),
                    }}
                  >
                    {turn.text}
                  </ReactMarkdown>
                </div>
              ) : (
                turn.text
              )}
            </div>
            {turn.tools && turn.tools.length > 0 && (
              <div className="tools">
                {turn.tools.map((tool) => (
                  <span key={tool} className="tool-chip">{tool}</span>
                ))}
              </div>
            )}
          </div>
        ))}

        {busy && (
          <div className="turn agent">
            <div className="bubble thinking">
              <span className="spinner" /> Searching…
            </div>
          </div>
        )}
      </div>

      <form className="chat-form" onSubmit={ask}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about courses, faculty, or times…"
          disabled={busy || loading}
        />
        <button type="submit" disabled={busy || loading || !draft.trim()}>Send</button>
      </form>
    </section>
  )
}
