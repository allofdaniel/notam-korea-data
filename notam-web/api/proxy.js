// Vercel Serverless Function - EC2 API 프록시 (임시: Lambda 대용량 처리 이슈)
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

    // EC2 API (안정적, 대용량 처리 가능)
    const EC2_API_URL = 'http://3.27.240.67:8000'
    const url = `${EC2_API_URL}${path || '/notams/stats'}`

    console.log('[Proxy] EC2:', url)

    const response = await fetch(url)
    const data = await response.json()

    res.status(200).json(data)
  } catch (error) {
    console.error('[Proxy Error]', error)
    res.status(500).json({ error: error.message })
  }
}
