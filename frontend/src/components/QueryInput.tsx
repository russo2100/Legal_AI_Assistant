import { useState } from 'react'
import TextField from '@mui/material/TextField'
import Button from '@mui/material/Button'
import SearchIcon from '@mui/icons-material/Search'
import Box from '@mui/material/Box'
import InputAdornment from '@mui/material/InputAdornment'

interface QueryInputProps {
  onSearch: (query: string) => void
  loading?: boolean
}

const QueryInput = ({ onSearch, loading = false }: QueryInputProps) => {
  const [query, setQuery] = useState('')

  const handleSearch = () => {
    if (query.trim()) {
      onSearch(query)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && query.trim()) {
      onSearch(query)
    }
  }

  return (
    <Box className="p-4">
      <TextField
        fullWidth
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="Введите ваш юридический вопрос или номер дела"
        variant="outlined"
        disabled={loading}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              <Button
                variant="contained"
                onClick={handleSearch}
                disabled={loading || !query.trim()}
                startIcon={<SearchIcon />}
              >
                Поиск
              </Button>
            </InputAdornment>
          ),
        }}
        sx={{
          '& .MuiOutlinedInput-root': {
            borderRadius: 2,
          },
        }}
      />
    </Box>
  )
}

export default QueryInput
