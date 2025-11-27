const express = require('express');
const router = express.Router();
const multer = require('multer');
const { uploadVideo, getVideos, getVideoById, deleteVideo, likeVideo, searchVideos } = require('../controllers/videoController');

const upload = multer({ storage: multer.memoryStorage() });

router.post('/upload', upload.single('video'), uploadVideo);
router.get('/', getVideos);
router.get('/:id', getVideoById);
router.delete('/:id', deleteVideo);
router.post('/:id/like', likeVideo);
router.get('/search', searchVideos);

module.exports = router;
