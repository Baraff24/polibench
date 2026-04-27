import { createBrowserRouter } from 'react-router'
import ErrorPage from './error-page'
import { HydrateFallback } from './fallback'
import Home, { loader as homeLoader } from './routes/home'
import Login from './routes/login'
import { Profile } from './routes/profile'
import Register from './routes/register'
import Root from './routes/root'
import SSOLogin, { loader as ssoLoader } from './routes/sso.login'
import Users, { loader as usersLoader } from './routes/users'
import Datasets, { loader as datasetsLoader } from './routes/datasets'
import DatasetDetail, { loader as datasetDetailLoader } from './routes/dataset-detail'
import DatasetVersionDetail, {
  loader as datasetVersionDetailLoader,
} from './routes/dataset-version-detail'
import PipelineDetail, { loader as pipelineDetailLoader } from './routes/pipeline-detail'
import Models, { loader as modelsLoader } from './routes/models'
import ModelDetail, { loader as modelDetailLoader } from './routes/model-detail'
import ExperimentDetail, { loader as experimentDetailLoader } from './routes/experiment-detail'
import Leaderboard from './routes/leaderboard'
import VerifyEmail from './routes/verify-email'
import { RequireAuth } from './components'
import CreateDataset from './routes/create-dataset.tsx'
import CreateModel from './routes/create-model.tsx'
import SubmitExperiment from './routes/submit-experiment.tsx'
import SubmitMetrics from './routes/submit-metrics.tsx'

export const routes = [
  {
    path: '/',
    Component: Root,
    errorElement: <ErrorPage />,
    children: [
      { index: true, Component: Home, HydrateFallback: HydrateFallback, loader: homeLoader },
      {
        path: 'sso-login-callback',
        Component: SSOLogin,
        loader: ssoLoader,
      },
      {
        path: 'profile',
        element: (
          <RequireAuth>
            <Profile />
          </RequireAuth>
        ),
      },
      {
        path: 'login',
        Component: Login,
      },
      {
        path: 'register',
        Component: Register,
      },
      {
        path: 'verify-email',
        Component: VerifyEmail,
      },
      {
        path: 'users',
        element: (
          <RequireAuth adminOnly>
            <Users />
          </RequireAuth>
        ),
        HydrateFallback: HydrateFallback,
        loader: usersLoader,
      },
      {
        path: 'leaderboard',
        Component: Leaderboard,
      },
      {
        path: 'datasets',
        Component: Datasets,
        HydrateFallback: HydrateFallback,
        loader: datasetsLoader,
      },
      {
        path: 'datasets/new',
        element: (
          <RequireAuth>
            <CreateDataset />
          </RequireAuth>
        ),
      },
      {
        path: 'datasets/:uuid',
        Component: DatasetDetail,
        HydrateFallback: HydrateFallback,
        loader: datasetDetailLoader,
      },
      {
        path: 'dataset-versions/:uuid',
        Component: DatasetVersionDetail,
        HydrateFallback: HydrateFallback,
        loader: datasetVersionDetailLoader,
      },
      {
        path: 'pipelines/:uuid',
        Component: PipelineDetail,
        HydrateFallback: HydrateFallback,
        loader: pipelineDetailLoader,
      },
      {
        path: 'models',
        Component: Models,
        HydrateFallback: HydrateFallback,
        loader: modelsLoader,
      },
      {
        path: 'models/new',
        element: (
          <RequireAuth>
            <CreateModel />
          </RequireAuth>
        ),
      },
      {
        path: 'models/:uuid',
        Component: ModelDetail,
        HydrateFallback: HydrateFallback,
        loader: modelDetailLoader,
      },
      {
        path: 'experiments/new',
        element: (
          <RequireAuth>
            <SubmitExperiment />
          </RequireAuth>
        ),
      },
      {
        path: 'experiments/:uuid',
        element: (
          <RequireAuth>
            <ExperimentDetail />
          </RequireAuth>
        ),
        HydrateFallback: HydrateFallback,
        loader: experimentDetailLoader,
      },
      {
        path: 'experiments/:uuid/metrics/new',
        element: (
          <RequireAuth>
            <SubmitMetrics />
          </RequireAuth>
        ),
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
