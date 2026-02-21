import AppBar from '@mui/material/AppBar'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import GavelIcon from '@mui/icons-material/Gavel'

const Header = () => (
  <AppBar position="static" color="primary">
    <Toolbar>
      <GavelIcon sx={{ mr: 2 }} />
      <Typography variant="h6" component="h1" sx={{ flexGrow: 1 }}>
        Юридический Ассистент
      </Typography>
    </Toolbar>
  </AppBar>
)

export default Header
