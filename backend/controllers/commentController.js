const Comment = require('../models/comment');

exports.addComment = async (req, res) => {
  const comment = await Comment.create({
    text: req.body.text,
    user: req.body.userId,
    video: req.body.videoId
  });
  res.json(comment);
};

exports.getComments = async (req, res) => {
  const comments = await Comment.find({ video: req.params.videoId }).populate('user');
  res.json(comments);
};

exports.deleteComment = async (req, res) => {
  await Comment.findByIdAndDelete(req.params.id);
  res.json({ message: 'Comment deleted' });
};
