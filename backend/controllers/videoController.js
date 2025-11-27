const Video = require('../models/video');
const { BlobServiceClient, StorageSharedKeyCredential } = require('@azure/storage-blob');
require('dotenv').config();

const account = process.env.AZURE_STORAGE_ACCOUNT_NAME;
const accountKey = process.env.AZURE_STORAGE_ACCOUNT_KEY;
const containerName = process.env.AZURE_CONTAINER_NAME;

const credentials = new StorageSharedKeyCredential(account, accountKey);
const blobServiceClient = new BlobServiceClient(
  `https://${account}.blob.core.windows.net`,
  credentials
);

exports.uploadVideo = async (req, res) => {
  try {
    const containerClient = blobServiceClient.getContainerClient(containerName);
    const file = req.file;
    const blobName = `videos/${Date.now()}-${file.originalname}`;
    const blockBlobClient = containerClient.getBlockBlobClient(blobName);

    await blockBlobClient.upload(file.buffer, file.size);
    const url = blockBlobClient.url;

    const video = await Video.create({
      title: req.body.title,
      description: req.body.description,
      url,
      user: req.body.userId
    });

    res.json(video);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.getVideos = async (req, res) => {
  const videos = await Video.find().populate('user').sort({ createdAt: -1 });
  res.json(videos);
};

exports.getVideoById = async (req, res) => {
  const video = await Video.findById(req.params.id).populate('user');
  res.json(video);
};

exports.deleteVideo = async (req, res) => {
  const video = await Video.findById(req.params.id);
  if(!video) return res.status(404).json({ error: 'Video not found' });
  await video.remove();
  res.json({ message: 'Video deleted' });
};

exports.likeVideo = async (req, res) => {
  const video = await Video.findById(req.params.id);
  if(!video) return res.status(404).json({ error: 'Video not found' });

  const index = video.likes.indexOf(req.body.userId);
  if(index === -1) video.likes.push(req.body.userId);
  else video.likes.splice(index, 1);

  await video.save();
  res.json(video);
};

exports.searchVideos = async (req, res) => {
  const query = req.query.q;
  const videos = await Video.find({ title: { $regex: query, $options: 'i' } }).populate('user');
  res.json(videos);
};
