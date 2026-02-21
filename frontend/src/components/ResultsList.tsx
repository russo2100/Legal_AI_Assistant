import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Chip from '@mui/material/Chip'
import DescriptionIcon from '@mui/icons-material/Description'
import GavelIcon from '@mui/icons-material/Gavel'

export interface SearchResult {
  id: string
  title: string
  type: 'norm' | 'case'
  description?: string
  source?: string
  date?: string
  number?: string
}

interface ResultsListProps {
  results: SearchResult[]
  onSelect: (result: SearchResult) => void
  selectedId?: string
}

const ResultsList = ({ results, onSelect, selectedId }: ResultsListProps) => {
  if (results.length === 0) {
    return (
      <Box className="p-8 text-center text-gray-500">
        <Typography variant="body1">
          Введите запрос для поиска нормативных актов и судебной практики
        </Typography>
      </Box>
    )
  }

  return (
    <Box className="p-4 space-y-2">
      {results.map((result) => (
        <Card
          key={result.id}
          className={`cursor-pointer transition-shadow hover:shadow-md ${
            selectedId === result.id ? 'border-2 border-primary-500' : ''
          }`}
          onClick={() => onSelect(result)}
        >
          <CardContent>
            <Box className="flex items-start justify-between mb-2">
              <Box className="flex items-center gap-2">
                {result.type === 'norm' ? (
                  <DescriptionIcon color="primary" fontSize="small" />
                ) : (
                  <GavelIcon color="secondary" fontSize="small" />
                )}
                <Typography variant="subtitle2" className="font-medium">
                  {result.title}
                </Typography>
              </Box>
              <Chip
                label={result.type === 'norm' ? 'Норма' : 'Дело'}
                size="small"
                color={result.type === 'norm' ? 'primary' : 'secondary'}
              />
            </Box>
            {result.description && (
              <Typography variant="body2" color="text.secondary" className="line-clamp-2">
                {result.description}
              </Typography>
            )}
            {(result.source || result.date || result.number) && (
              <Box className="mt-2 flex flex-wrap gap-2">
                {result.source && (
                  <Typography variant="caption" color="text.secondary">
                    {result.source}
                  </Typography>
                )}
                {result.date && (
                  <Typography variant="caption" color="text.secondary">
                    {result.date}
                  </Typography>
                )}
                {result.number && (
                  <Typography variant="caption" color="text.secondary">
                    № {result.number}
                  </Typography>
                )}
              </Box>
            )}
          </CardContent>
        </Card>
      ))}
    </Box>
  )
}

export default ResultsList
