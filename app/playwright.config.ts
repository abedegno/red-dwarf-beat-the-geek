import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir:'./e2e',timeout:600000,workers:1,retries:0,
  use:{baseURL:process.env.GAME_URL ?? 'http://127.0.0.1:4173',viewport:{width:1100,height:850},hasTouch:true,
    screenshot:'only-on-failure',trace:'retain-on-failure'},
  projects:[...(process.env.GAME_WEBKIT?[{name:'webkit',use:{browserName:'webkit' as const}}]:[]),{name:'chrome',use:{browserName:'chromium',launchOptions:{
    ...(process.env.BTG_CHROME_PATH?{executablePath:process.env.BTG_CHROME_PATH}:{})}}}],
});
