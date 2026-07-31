import { useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL;

const translations = {
  en: {
    language: 'Language',
    badge: 'AI video summarizer',
    title: 'Turn videos into clear summaries',
    description:
      'Paste a YouTube link and receive a concise summary in the original language of the video.',
    label: 'YouTube video URL',
    placeholder: 'https://www.youtube.com/watch?v=...',
    button: 'Generate summary',
    loadingButton: 'Generating...',
    loadingMessage: 'Extracting the transcript and generating the summary...',
    emptyUrl: 'Enter a YouTube video URL.',
    genericError: 'Unable to generate the video summary.',
    unexpectedError: 'An unexpected error occurred.',
    resultTitle: 'Video summary',
    transcriptLanguage: 'Detected language',
    transcriptSize: 'Transcript size',
    characters: 'characters',
  },
  pt: {
    language: 'Idioma',
    badge: 'Resumo de vídeos com IA',
    title: 'Transforme vídeos em resumos claros',
    description:
      'Cole o link de um vídeo do YouTube e receba um resumo no idioma original do conteúdo.',
    label: 'URL do vídeo do YouTube',
    placeholder: 'https://www.youtube.com/watch?v=...',
    button: 'Gerar resumo',
    loadingButton: 'Gerando...',
    loadingMessage: 'Extraindo a legenda e gerando o resumo...',
    emptyUrl: 'Informe a URL de um vídeo do YouTube.',
    genericError: 'Não foi possível gerar o resumo do vídeo.',
    unexpectedError: 'Ocorreu um erro inesperado.',
    resultTitle: 'Resumo do vídeo',
    transcriptLanguage: 'Idioma identificado',
    transcriptSize: 'Tamanho da legenda',
    characters: 'caracteres',
  },
}

function App() {
  const [interfaceLanguage, setInterfaceLanguage] = useState('en')
  const [videoUrl, setVideoUrl] = useState('')
  const [summary, setSummary] = useState('')
  const [transcriptLanguage, setTranscriptLanguage] = useState('')
  const [transcriptCharacters, setTranscriptCharacters] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const text = translations[interfaceLanguage]

  async function handleSubmit(event) {
    event.preventDefault()

    const normalizedUrl = videoUrl.trim()

    if (!normalizedUrl) {
      setError(text.emptyUrl)
      return
    }

    setLoading(true)
    setError('')
    setSummary('')
    setTranscriptLanguage('')
    setTranscriptCharacters(null)

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: normalizedUrl,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.message || data.error || text.genericError)
      }

      setSummary(data.summary || data.resumo || '')
      setTranscriptLanguage(data.transcriptLanguage || '')
      setTranscriptCharacters(data.transcriptCharacters ?? null)
    } catch (requestError) {
      console.error(requestError)

      setError(
        requestError instanceof Error
          ? requestError.message
          : text.unexpectedError,
      )
    } finally {
      setLoading(false)
    }
  }

  function handleLanguageChange(event) {
    setInterfaceLanguage(event.target.value)
    setError('')
  }

  return (
    <main className="app">
      <div className="background-glow background-glow-one" />
      <div className="background-glow background-glow-two" />

      <section className="page-container">
        <nav className="topbar">
          <a className="brand" href="/" aria-label="Video Summary home">
            <span className="brand-icon" aria-hidden="true">
              ▶
            </span>
            <span>Video Summary</span>
          </a>

          <div className="language-selector">
            <label htmlFor="interface-language">{text.language}</label>

            <select
              id="interface-language"
              value={interfaceLanguage}
              onChange={handleLanguageChange}
              aria-label={text.language}
            >
              <option value="en">English</option>
              <option value="pt">Português</option>
            </select>
          </div>
        </nav>

        <section className="hero-section">
          <span className="badge">{text.badge}</span>

          <h1>{text.title}</h1>

          <p className="hero-description">{text.description}</p>

          <form className="summary-form" onSubmit={handleSubmit}>
            <label htmlFor="video-url">{text.label}</label>

            <input
              id="video-url"
              type="url"
              inputMode="url"
              autoComplete="url"
              placeholder={text.placeholder}
              value={videoUrl}
              onChange={(event) => setVideoUrl(event.target.value)}
              disabled={loading}
              required
            />

            <button type="submit" disabled={loading}>
              {loading && <span className="button-spinner" aria-hidden="true" />}
              {loading ? text.loadingButton : text.button}
            </button>
          </form>

          {error && (
            <div className="message error-message" role="alert">
              <span aria-hidden="true">!</span>
              <p>{error}</p>
            </div>
          )}

          {loading && (
            <div className="message loading-message" role="status">
              <span className="loading-spinner" aria-hidden="true" />
              <p>{text.loadingMessage}</p>
            </div>
          )}
        </section>

        {summary && (
          <section className="result-card">
            <header className="result-header">
              <div>
                <span className="result-label">{text.resultTitle}</span>

                <div className="result-metadata">
                  {transcriptLanguage && (
                    <span>
                      {text.transcriptLanguage}: {transcriptLanguage}
                    </span>
                  )}

                  {transcriptCharacters !== null && (
                    <span>
                      {text.transcriptSize}: {transcriptCharacters}{' '}
                      {text.characters}
                    </span>
                  )}
                </div>
              </div>
            </header>

            <article className="summary-content">{summary}</article>
          </section>
        )}
      </section>
    </main>
  )
}

export default App