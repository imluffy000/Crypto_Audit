export const mockRepositories = [
  {
    id: 'repo-cryptoauth',
    name: 'CryptoAuth',
    owner: 'github-user',
    description: 'Cryptographic authentication library',
    branch: 'main',
    visibility: 'Public',
    lastUpdated: '2 days ago',
    files: 142,
    size: 4.8,
    status: 'Ready to scan',
    tree: {
      name: 'CryptoAuth',
      type: 'folder',
      children: [
        {
          name: 'src',
          type: 'folder',
          children: [
            {
              name: 'auth',
              type: 'folder',
              children: [
                { name: 'login.py', type: 'file', size: 18420, ext: '.py' },
                { name: 'session.py', type: 'file', size: 22130, ext: '.py' },
              ],
            },
            {
              name: 'crypto',
              type: 'folder',
              children: [
                { name: 'encryption.py', type: 'file', size: 32780, ext: '.py' },
                { name: 'hashing.py', type: 'file', size: 21445, ext: '.py' },
                { name: 'keys.py', type: 'file', size: 25660, ext: '.py' },
              ],
            },
            {
              name: 'api',
              type: 'folder',
              children: [{ name: 'routes.py', type: 'file', size: 16320, ext: '.py' }],
            },
            {
              name: 'config',
              type: 'folder',
              children: [{ name: 'settings.py', type: 'file', size: 15320, ext: '.py' }],
            },
          ],
        },
        {
          name: 'tests',
          type: 'folder',
          children: [
            { name: 'test_auth.py', type: 'file', size: 12540, ext: '.py' },
            { name: 'test_crypto.py', type: 'file', size: 18320, ext: '.py' },
          ],
        },
        { name: 'requirements.txt', type: 'file', size: 840, ext: '.txt' },
        { name: 'README.md', type: 'file', size: 7360, ext: '.md' },
        { name: '.gitignore', type: 'file', size: 460, ext: '.gitignore' },
      ],
    },
  },
  {
    id: 'repo-security-demo',
    name: 'security-demo',
    owner: 'security-team',
    description: 'Security demo application',
    branch: 'develop',
    visibility: 'Private',
    lastUpdated: '5 days ago',
    files: 88,
    size: 2.8,
    status: 'Ready to scan',
    tree: {
      name: 'security-demo',
      type: 'folder',
      children: [
        { name: 'src', type: 'folder', children: [{ name: 'app.js', type: 'file', size: 28450, ext: '.js' }] },
        { name: 'docs', type: 'folder', children: [{ name: 'overview.md', type: 'file', size: 9400, ext: '.md' }] },
        { name: 'package.json', type: 'file', size: 1120, ext: '.json' },
      ],
    },
  },
  {
    id: 'repo-payment-api',
    name: 'payment-api',
    owner: 'finance-team',
    description: 'Payment processing API',
    branch: 'main',
    visibility: 'Public',
    lastUpdated: '1 week ago',
    files: 64,
    size: 1.9,
    status: 'Ready to scan',
    tree: {
      name: 'payment-api',
      type: 'folder',
      children: [
        { name: 'src', type: 'folder', children: [{ name: 'routes.ts', type: 'file', size: 21930, ext: '.ts' }] },
        { name: 'README.md', type: 'file', size: 6650, ext: '.md' },
        { name: 'tsconfig.json', type: 'file', size: 920, ext: '.json' },
      ],
    },
  },
];

export const githubRepositories = mockRepositories;
