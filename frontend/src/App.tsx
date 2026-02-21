import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import Home from './pages/Home'
import DocumentDraft from './pages/DocumentDraft'
import CaseSearch from './pages/CaseSearch'

const theme = createTheme({
  palette: {
    primary: {
      main: '#0284c7',
    },
    secondary: {
      main: '#64748b',
    },
  },
  typography: {
    fontFamily: '"Segoe UI", "Roboto", "Helvetica", "Arial", sans-serif',
  },
})

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/document-draft" element={<DocumentDraft />} />
          <Route path="/case-search" element={<CaseSearch />} />
        </Routes>
      </Router>
    </ThemeProvider>
  )
}

export default App
