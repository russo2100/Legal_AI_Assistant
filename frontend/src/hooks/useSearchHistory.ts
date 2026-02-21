import { useState, useEffect } from 'react'

const HISTORY_KEY = 'yurik_search_history'
const MAX_HISTORY = 10

export const useSearchHistory = () => {
  const [history, setHistory] = useState<string[]>([])

  useEffect(() => {
    const saved = localStorage.getItem(HISTORY_KEY)
    if (saved) {
      try {
        setHistory(JSON.parse(saved))
      } catch {
        setHistory([])
      }
    }
  }, [])

  const addToHistory = (query: string) => {
    setHistory((prev) => {
      const filtered = prev.filter((item) => item !== query)
      const updated = [query, ...filtered].slice(0, MAX_HISTORY)
      localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
      return updated
    })
  }

  const clearHistory = () => {
    setHistory([])
    localStorage.removeItem(HISTORY_KEY)
  }

  return {
    history,
    addToHistory,
    clearHistory,
  }
}
