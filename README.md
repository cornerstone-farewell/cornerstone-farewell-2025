# 🎓 Cornerstone International School - Farewell 2025

A complete farewell memory website system with file uploads, admin panel, and memory wall.

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/cornerstone-farewell.git
cd cornerstone-farewell
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Create Required Folders
```bash
mkdir -p uploads database
```

### 4. Start Server
```bash
# Development
node server.js

# Production (with PM2)
npm install -g pm2
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### 5. Access Website
- **Website:** `http://YOUR_SERVER_IP:3000`
- **Admin Panel:** Click logo 5 times OR go to `http://YOUR_SERVER_IP:3000/#admin`
- **Admin Password:** `cornerstone2025` (change in server.js)

## 📦 Features

- ✅ Drag & drop file uploads (images + videos)
- ✅ 200MB total upload limit per submission
- ✅ Memory wall with masonry grid
- ✅ Admin approval system
- ✅ Like functionality
- ✅ Download all as ZIP
- ✅ SQLite database (no external DB needed)
- ✅ Auto-restart with PM2
- ✅ Mobile responsive

## 🔧 Configuration

Edit `server.js` to change:
- `ADMIN_PASSWORD` - Admin login password
- `PORT` - Server port (default: 3000)
- `MAX_TOTAL_SIZE` - Max upload size (default: 200MB)

## 📂 File Storage

- **Uploads:** `./uploads/` folder
- **Database:** `./database/memories.db`

## 🔄 After VM Restart

If using PM2:
```bash
pm2 resurrect
```

If not using PM2:
```bash
cd cornerstone-farewell
node server.js
```

## 🛡️ Security Notes

1. Change the admin password immediately
2. Set up HTTPS with nginx reverse proxy
3. Configure firewall (allow port 3000)
4. Regular backups of uploads/ and database/ folders

## 📜 License

MIT License - Cornerstone International School 2025


compilations in admin is not working
fun features in admin is not wokring
detinations approve all says no admin token found please lgon again
watch as movie says it need admin approved images
clicking on drag and drop ur files is ding nothing
memory compilations say comp memories somethingis not defined, so no playing o ememory compilatiins
turoail button is not there for the website with no tutroial for stuff
navbar does not cotain all rutes
senior advice says cannot read properties of undefined, push somehting
student import list has to be better, it does ot hae a fixed thing for the bulk thingie
timeline also did not load, it shows old one...
though i kept messae in gratitude wall i the thing, it is not reflecting for acceptance on admin side
for class superlative, it has to be section wise same list duplicated with diff students i have to import the student sin the thing in the admin thingie
i poted in wish jar,but not reflectingn admin side
i posted i song dedications, but not reflectig on admin side
a person has to be able toedit thir mood in the thig
mood not reflecting in admin dashboard, though no approvl i sneeded
time capsule adin approvial not appraring
destinations approve ll saying no admin toke n found and all...
music config in setting has ot be upload the music mode... or select existing music fro aerver... not tyoe the path, for all this is same
boombox ui is way too bad
memory compilations appeared twice
for some reason, we have two mail garbage tht is there