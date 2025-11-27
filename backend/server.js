const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();

const authRoutes = require('./routes/auth');
const videoRoutes = require('./routes/videos');
const commentRoutes = require('./routes/comments');

const app = express();
app.use(cors());
app.use(express.json());

mongoose.connect(process.env.MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true })
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.log(err));

app.use('/api/auth', authRoutes);
app.use('/api/videos', videoRoutes);
app.use('/api/comments', commentRoutes);

app.listen(process.env.PORT, () => console.log(`Server running on port ${process.env.PORT}`));
