import { useNavigate } from 'react-router'
import { useAuth } from '../contexts/auth'

export async function loader() {
  return null
}

export default function Home() {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <>
      {/* Hero */}
      <section className='hero'>
        <span className='hero__badge'>Open-source benchmarking platform</span>
        <h1 className='hero__title'>
          Compare recommender systems.
          <br />
          <span className='hero__title--accent'>Objectively.</span>
        </h1>
        <p className='hero__subtitle'>
          Polibench lets researchers and engineers register datasets, algorithms and experiments in
          one place — then rank models on standardised metrics with a public leaderboard.
        </p>
        <div className='hero__actions'>
          <button className='btn btn--primary btn--lg' onClick={() => navigate('/leaderboard')}>
            View Leaderboard
          </button>
          {user === undefined && (
            <button className='btn btn--outline btn--lg' onClick={() => navigate('/register')}>
              Get Started
            </button>
          )}
        </div>
      </section>

      {/* How it works */}
      <section className='how'>
        <div className='how__header'>
          <h2 className='how__title'>How it works</h2>
          <p className='how__desc'>Three steps — from raw data to a ranked leaderboard.</p>
        </div>

        <div className='how__grid'>
          <div className='how__step'>
            <div className='how__step-number'>1</div>
            <h3 className='how__step-title'>Register a dataset</h3>
            <p className='how__step-desc'>
              Upload metadata for your recommendation dataset — task type, splits, version. Public
              or private.
            </p>
          </div>
          <div className='how__step'>
            <div className='how__step-number'>2</div>
            <h3 className='how__step-title'>Submit experiments</h3>
            <p className='how__step-desc'>
              Run your algorithm, then submit the experiment with seed, training config and code
              reference for reproducibility.
            </p>
          </div>
          <div className='how__step'>
            <div className='how__step-number'>3</div>
            <h3 className='how__step-title'>Check the leaderboard</h3>
            <p className='how__step-desc'>
              Metrics are ranked automatically. Filter by dataset, split and metric — see who is on
              top.
            </p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className='highlights'>
        <div className='highlights__grid'>
          <div className='highlights__card'>
            <svg
              className='highlights__icon'
              viewBox='0 0 24 24'
              fill='none'
              stroke='currentColor'
              strokeWidth='1.5'
            >
              <rect x='3' y='3' width='7' height='7' rx='1' />
              <rect x='14' y='3' width='7' height='7' rx='1' />
              <rect x='3' y='14' width='7' height='7' rx='1' />
              <rect x='14' y='14' width='7' height='7' rx='1' />
            </svg>
            <h3 className='highlights__card-title'>UUID-first API</h3>
            <p className='highlights__card-desc'>
              Every entity is identified by UUID — no internal database IDs leak to clients. Stable,
              DB-agnostic and safe.
            </p>
          </div>
          <div className='highlights__card'>
            <svg
              className='highlights__icon'
              viewBox='0 0 24 24'
              fill='none'
              stroke='currentColor'
              strokeWidth='1.5'
            >
              <path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z' />
            </svg>
            <h3 className='highlights__card-title'>Reproducibility</h3>
            <p className='highlights__card-desc'>
              Every experiment stores seed, training config, git commit and Docker image — so
              results can be verified and reproduced.
            </p>
          </div>
          <div className='highlights__card'>
            <svg
              className='highlights__icon'
              viewBox='0 0 24 24'
              fill='none'
              stroke='currentColor'
              strokeWidth='1.5'
            >
              <path d='M18 20V10M12 20V4M6 20v-6' />
            </svg>
            <h3 className='highlights__card-title'>Live leaderboard</h3>
            <p className='highlights__card-desc'>
              Metrics are denormalised for fast queries — leaderboard results come from indexed
              reads, no aggregation needed.
            </p>
          </div>
          <div className='highlights__card'>
            <svg
              className='highlights__icon'
              viewBox='0 0 24 24'
              fill='none'
              stroke='currentColor'
              strokeWidth='1.5'
            >
              <path d='M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2' />
              <circle cx='9' cy='7' r='4' />
              <path d='M23 21v-2a4 4 0 00-3-3.87' />
              <path d='M16 3.13a4 4 0 010 7.75' />
            </svg>
            <h3 className='highlights__card-title'>Teams</h3>
            <p className='highlights__card-desc'>
              Group researchers into teams — submit experiments together and filter leaderboards by
              team.
            </p>
          </div>
        </div>
      </section>

      {/* Stack */}
      <section className='stack-section'>
        <h2 className='stack-section__title'>Built with</h2>
        <div className='stack-section__row'>
          {['FastAPI', 'React', 'MongoDB', 'Docker', 'Beanie', 'Pydantic'].map((name) => (
            <span key={name} className='hero__stack-item'>
              {name}
            </span>
          ))}
        </div>
      </section>
    </>
  )
}
