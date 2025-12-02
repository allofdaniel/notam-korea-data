// Vercel Serverless Function - Lambda API 프록시
export default async function handler(req, res) {
  // CORS 설정
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')

  if (req.method === 'OPTIONS') {
    return res.status(200).end()
  }

  try {
    const { path } = req.query

    // Lambda API (서버리스 - $0/월)
    const LAMBDA_API_URL = 'https://b5hg4r5aoqoit35vhxzo2v75wi0vryxq.lambda-url.ap-southeast-2.on.aws'
    const url = `${LAMBDA_API_URL}${path || '/health'}`

    console.log('[Proxy] Lambda:', url)

    const response = await fetch(url)
    const data = await response.json()

    res.status(200).json(data)
  } catch (error) {
    console.error('[Proxy Error]', error)
    res.status(500).json({ error: error.message })
  }
}
