const mongoose = require('mongoose');
const videoSchema = new mongoose.Schema({
  title: { type: String, required: true },
  description: String,
  url: { type: String, required: true },
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  likes: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
  createdAt: { type: Date, default: Date.now }
});
module.exports = mongoose.model('Video', videoSchema);
