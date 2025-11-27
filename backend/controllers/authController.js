const User = require('../models/user');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

exports.register = async (req, res) => {
  try {
    const { username, email, password } = req.body;
    const hashed = await bcrypt.hash(password, 10);
    const user = await User.create({ username, email, password: hashed });
    res.json({ message: 'User created', user });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.login = async (req, res) => {
  try {
    const { email, password } = req.body;
    const user = await User.findOne({ email });
    if(!user) return res.status(404).json({ error: 'User not found' });

    const valid = await bcrypt.compare(password, user.password);
    if(!valid) return res.status(400).json({ error: 'Invalid password' });

    const token = jwt.sign({ id: user._id }, process.env.JWT_SECRET, { expiresIn: '7d' });
    res.json({ message: 'Login successful', token, user });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};
