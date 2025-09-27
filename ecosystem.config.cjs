module.exports = {
  apps: [
    {
      name: 'webapp-frontend',
      script: 'npx',
      args: 'wrangler pages dev dist --ip 0.0.0.0 --port 3000',
      env: {
        NODE_ENV: 'development',
        PORT: 3000
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork',
      restart_delay: 5000,
      max_restarts: 10
    },
    {
      name: 'python-rag-server',
      script: 'python3',
      args: 'python_rag/api/simple_main.py',
      cwd: '/home/user/webapp',
      env: {
        PYTHONPATH: '/home/user/webapp',
        PORT: 8000
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork',
      restart_delay: 5000,
      max_restarts: 10
    }
  ]
}