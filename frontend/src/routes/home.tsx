import { useLoaderData } from 'react-router'

type Feature = {
  img: string
  alt: string
  title: string
  desc: string
  github: string
  stars: number | null
}

type FeaturesCache = {
  date: string
  features: Feature[]
}

const FEATURES: Feature[] = [
  {
    img: 'react-router-mark.svg',
    alt: 'react-router',
    title: 'React Router',
    desc: "React Router provides clean routing between the app's views.",
    github: 'remix-run/react-router',
    stars: null,
  },
  {
    img: 'vite.svg',
    alt: 'vite',
    title: 'Vite',
    desc: 'Vite is the next-generation frontend tooling: fast builds, instant HMR and zero config.',
    github: 'vitejs/vite',
    stars: null,
  },
  {
    img: 'hook-forms.svg',
    alt: 'react-hook-form',
    title: 'React Hook Form',
    desc: 'Intuitive and flexible form management with minimal re-renders.',
    github: 'react-hook-form/react-hook-form',
    stars: null,
  },
  {
    img: 'fastapi-mark.svg',
    alt: 'fastapi',
    title: 'FastAPI',
    desc: 'FastAPI handles your backend: fast, production-ready APIs with automatic OpenAPI docs.',
    github: 'tiangolo/fastapi',
    stars: null,
  },
  {
    img: 'beanie.svg',
    alt: 'beanie',
    title: 'Beanie',
    desc: 'Async Python ODM for MongoDB built on Pydantic — typed models, indexes, queries.',
    github: 'roman-right/beanie',
    stars: null,
  },
  {
    img: 'mongodb.png',
    alt: 'mongodb',
    title: 'MongoDB',
    desc: 'Document database with flexible schema, powerful aggregations and compound indexes.',
    github: 'mongodb/mongo',
    stars: null,
  },
]

export async function loader() {
  const today = new Date().toDateString()
  const cacheValue = localStorage.getItem('polibench-features')
  if (cacheValue !== null) {
    const cache = JSON.parse(cacheValue) as FeaturesCache
    if (cache.date === today) return { features: cache.features }
  }

  const data = await Promise.all(
    FEATURES.map((f) => fetch(`https://api.github.com/repos/${f.github}`)),
  )
  const results = await Promise.all(data.map((r) => r.json()))
  const features = FEATURES.map((f, i) => ({ ...f, stars: results[i].stargazers_count ?? null }))
  localStorage.setItem('polibench-features', JSON.stringify({ date: today, features }))
  return { features }
}

const fmt = Intl.NumberFormat('en', { notation: 'compact', maximumSignificantDigits: 3 })

export default function Home() {
  const { features } = useLoaderData() as { features: Feature[] }

  return (
    <>
      {/* Hero */}
      <section className='hero'>
        <h1 className='hero__title'>Polibench</h1>
        <p className='hero__subtitle'>
          A benchmarking platform for recommender systems. Register datasets, algorithms and
          experiments — consult the leaderboard.
        </p>
        <div className='hero__stack'>
          {['FastAPI', 'React', 'MongoDB', 'Docker'].map((name) => (
            <span key={name} className='hero__stack-item'>
              {name}
            </span>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className='features'>
        <div className='features__header'>
          <h2 className='features__title'>Built with</h2>
          <p className='features__desc'>
            A minimal, production-ready stack — only what you actually need.
          </p>
        </div>
        <div className='card-grid'>
          {features.map((f) => {
            let githubLabel = 'GitHub'
            if (f.stars) {
              githubLabel = fmt.format(f.stars)
            }
            return (
              <article key={f.title} className='card'>
                <img className='card__media' src={f.img} alt={f.alt} />
                <div className='card__body'>
                  <h3 className='card__title'>{f.title}</h3>
                  <p className='card__desc'>{f.desc}</p>
                </div>
                {f.github && (
                  <div className='card__footer'>
                    <a
                      className='btn btn--outline btn--sm'
                      href={`https://github.com/${f.github}`}
                      target='_blank'
                      rel='noreferrer'
                    >
                      <svg className='btn__icon' viewBox='0 0 24 24' fill='currentColor'>
                        <path d='M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.49.5.09.68-.22.68-.48v-1.69c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.52 2.34 1.08 2.91.83.09-.65.35-1.08.63-1.33-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.56 9.56 0 0 1 12 6.8c.85 0 1.71.11 2.51.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10.01 10.01 0 0 0 22 12c0-5.52-4.48-10-10-10z' />
                      </svg>
                      {githubLabel}
                    </a>
                  </div>
                )}
              </article>
            )
          })}
        </div>
      </section>
    </>
  )
}
