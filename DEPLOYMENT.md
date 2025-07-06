# 🚀 Vercel Deployment Guide

## Quick Start

1. **Fork/Clone this repository** to your GitHub account

2. **Connect to Vercel**:

   - Go to [vercel.com](https://vercel.com)
   - Sign up/Login with GitHub
   - Click "New Project"
   - Import your repository

3. **Configure Settings**:

   - Framework Preset: `Other`
   - Build Command: Leave empty
   - Output Directory: Leave empty
   - Install Command: `pip install -r requirements.txt`

4. **Deploy** 🎉
   - Click "Deploy"
   - Wait for deployment to complete
   - Your app will be live at `https://your-app-name.vercel.app`

## Configuration Files

- ✅ `vercel.json` - Vercel configuration
- ✅ `runtime.txt` - Python version specification
- ✅ `.vercelignore` - Files to exclude from deployment

## Environment Variables (Optional)

In Vercel dashboard, you can set:

```
MAX_FILE_SIZE=20971520  # 20MB (recommended for Vercel)
PROCESSING_TIMEOUT=45   # 45 seconds (under 60s limit)
```

## Limitations on Vercel

- ⏱️ **Function Timeout**: 60 seconds maximum
- 💾 **File Storage**: Temporary only (files deleted after response)
- 🔄 **Stateless**: Each request is independent
- 📐 **Recommended File Size**: 10-20MB for optimal performance

## Troubleshooting

### Common Issues:

1. **Timeout Errors**:

   - Reduce file size
   - Use lower DPI settings
   - Process fewer pages at once

2. **Memory Issues**:

   - Optimize image processing
   - Reduce concurrent operations

3. **Cold Start Delays**:
   - First request may take 10-15 seconds
   - Subsequent requests are faster

## Alternative Deployment Options

If Vercel limitations are too restrictive:

- 🐳 **Docker + Cloud Run**: Better for large files
- 🖥️ **Traditional VPS**: Full control over resources
- ☁️ **AWS Lambda**: Similar to Vercel but configurable limits
- 🔥 **Railway/Render**: Good middle ground

## Support

Need help with deployment? Check our [main README](README.md) or open an issue!
