const express = require('express');
const router = express.Router();
const { addComment, getComments, deleteComment } = require('../controllers/commentController');

router.post('/', addComment);
router.get('/:videoId', getComments);
router.delete('/:id', deleteComment);

module.exports = router;
