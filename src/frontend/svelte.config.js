import adapter from '@sveltejs/adapter-static';

const config = { kit: { adapter: adapter({ strict: false }) } };

export default config;
