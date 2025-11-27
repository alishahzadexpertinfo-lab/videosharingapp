const mongoose = require('mongoose');
const commentSchema = new mongoose.Schema({
  text: String,
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  video: { type: mongoose.Schema.Types.ObjectId, ref: 'Video' },
  createdAt: { type: Date, default: Date.now }
});
module.exports = mongoose.model('Comment', commentSchema);
