import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'
import HistoryIcon from '@mui/icons-material/History'
import Box from '@mui/material/Box'

interface SidebarProps {
  history: string[]
  onSelectHistory: (query: string) => void
}

const Sidebar = ({ history, onSelectHistory }: SidebarProps) => (
  <Box className="w-full md:w-64 bg-gray-100 border-r border-gray-200 h-full overflow-y-auto">
    <Box className="p-4 border-b border-gray-200">
      <Typography variant="subtitle1" className="font-bold flex items-center gap-2">
        <HistoryIcon fontSize="small" />
        История запросов
      </Typography>
    </Box>
    <List dense>
      {history.length === 0 ? (
        <Typography variant="body2" color="text.secondary" className="p-4 text-center">
          История пуста
        </Typography>
      ) : (
        history.map((item, index) => (
          <ListItem key={index} disablePadding>
            <ListItemButton onClick={() => onSelectHistory(item)}>
              <ListItemText
                primary={item}
                primaryTypographyProps={{
                  variant: 'body2',
                  noWrap: true,
                }}
              />
            </ListItemButton>
          </ListItem>
        ))
      )}
    </List>
  </Box>
)

export default Sidebar
