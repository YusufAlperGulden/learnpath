-- Automatically creates the isolated pytest database on first container boot
SELECT 'CREATE DATABASE learnpath_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'learnpath_test')\gexec
