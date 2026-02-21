import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Header from '../components/Header'

const CaseSearch = () => (
  <div className="h-screen flex flex-col">
    <Header />
    <Box className="flex-1 flex items-center justify-center p-8">
      <Typography variant="h5" color="text.secondary">
        Поиск дел (в разработке)
      </Typography>
    </Box>
  </div>
)

export default CaseSearch
