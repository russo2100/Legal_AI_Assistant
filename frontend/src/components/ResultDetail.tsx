import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import Chip from '@mui/material/Chip'
import DescriptionIcon from '@mui/icons-material/Description'
import GavelIcon from '@mui/icons-material/Gavel'
import CalendarTodayIcon from '@mui/icons-material/CalendarToday'
import ArticleIcon from '@mui/icons-material/Article'
import type { SearchResult } from './ResultsList'

interface ResultDetailProps {
  result: SearchResult | null
}

const ResultDetail = ({ result }: ResultDetailProps) => {
  if (!result) {
    return (
      <Box className="p-8 text-center text-gray-500 h-full flex items-center justify-center">
        <Typography variant="body1">
          Выберите результат из списка для просмотра деталей
        </Typography>
      </Box>
    )
  }

  return (
    <Card className="h-full">
      <CardContent className="h-full flex flex-col">
        <Box className="flex items-center gap-2 mb-4">
          {result.type === 'norm' ? (
            <DescriptionIcon color="primary" />
          ) : (
            <GavelIcon color="secondary" />
          )}
          <Chip
            label={result.type === 'norm' ? 'Нормативный акт' : 'Судебное дело'}
            color={result.type === 'norm' ? 'primary' : 'secondary'}
          />
        </Box>

        <Typography variant="h5" className="font-bold mb-4">
          {result.title}
        </Typography>

        <Divider className="mb-4" />

        <Box className="space-y-4 flex-grow">
          {result.number && (
            <Box className="flex items-center gap-2">
              <ArticleIcon fontSize="small" color="action" />
              <Typography variant="body2">
                <strong>Номер:</strong> {result.number}
              </Typography>
            </Box>
          )}

          {result.date && (
            <Box className="flex items-center gap-2">
              <CalendarTodayIcon fontSize="small" color="action" />
              <Typography variant="body2">
                <strong>Дата:</strong> {result.date}
              </Typography>
            </Box>
          )}

          {result.source && (
            <Box>
              <Typography variant="body2">
                <strong>Источник:</strong> {result.source}
              </Typography>
            </Box>
          )}

          {result.description && (
            <Box>
              <Typography variant="subtitle2" className="mb-2">
                Описание:
              </Typography>
              <Typography variant="body2" className="whitespace-pre-line">
                {result.description}
              </Typography>
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  )
}

export default ResultDetail
