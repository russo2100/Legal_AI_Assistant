import { useState } from 'react'
import Header from '../components/Header'
import Sidebar from '../components/Sidebar'
import QueryInput from '../components/QueryInput'
import ResultsList from '../components/ResultsList'
import ResultDetail from '../components/ResultDetail'
import CircularProgress from '@mui/material/CircularProgress'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Alert from '@mui/material/Alert'
import type { SearchResult } from '../components/ResultsList'
import { useSearchResults } from '../hooks/useSearchResults'
import { useSearchHistory } from '../hooks/useSearchHistory'

const Home = () => {
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null)
  const { results, loading, error, search } = useSearchResults()
  const { history, addToHistory, clearHistory } = useSearchHistory()

  const handleSearch = async (query: string) => {
    addToHistory(query)
    await search(query)
    setSelectedResult(null)
  }

  const handleSelectHistory = (query: string) => {
    handleSearch(query)
  }

  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar history={history} onSelectHistory={handleSelectHistory} />
        <main className="flex-1 flex flex-col md:flex-row overflow-hidden">
          <div className="w-full md:w-1/2 border-r border-gray-200 overflow-y-auto">
            <QueryInput onSearch={handleSearch} loading={loading} />
            
            {loading && (
              <Box className="flex justify-center p-8">
                <CircularProgress />
              </Box>
            )}

            {error && (
              <Box className="p-4">
                <Alert severity="error">{error}</Alert>
              </Box>
            )}

            {!loading && !error && (
              <ResultsList
                results={results}
                onSelect={setSelectedResult}
                selectedId={selectedResult?.id}
              />
            )}
          </div>

          <div className="hidden md:block md:w-1/2 overflow-y-auto">
            <ResultDetail result={selectedResult} />
          </div>
        </main>
      </div>
    </div>
  )
}

export default Home
