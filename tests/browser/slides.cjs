const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 await page.route('https://www.mentimeter.com/**',r=>r.abort());
 const origin=process.env.FIBOLAB_TEST_URL||'http://127.0.0.1:8080';
 for(const entry of ['index.html','lesson.html']){
  await page.goto(origin+'/'+entry);
  assert.equal(await page.locator('iframe[src*="mentimeter"]').count(),2);
  await page.getByText('COMP 1023 · INTRODUCTION TO COMPUTER SCIENCE',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Reveal the answer',exact:true}).first().click();
  await page.locator('.slide.active .answer.show').waitFor();
  for(let i=0;i<5;i++) await page.getByRole('button',{name:'Next →',exact:true}).click();
  await page.getByRole('link',{name:'Open FiboLab'}).waitFor();
  assert.equal(await page.locator('.slide.active img[alt="Scan to open FiboLab"]').evaluate(img=>img.complete&&img.naturalWidth>0&&img.src.startsWith('data:image/')),true);
  assert.equal(await page.getByRole('link',{name:'Open FiboLab'}).getAttribute('href'),origin+'/lab/');
  for(let i=0;i<2;i++) await page.getByRole('button',{name:'Next →',exact:true}).click();
  const frame=page.frameLocator('iframe[title="FiboLab live class leaderboard"]');
  await frame.getByText('Live leaderboard',{exact:true}).waitFor();
  await page.screenshot({path:'/tmp/fibolab-'+entry+'.png',fullPage:true});
 }
 await browser.close();console.log('PASS: both slide entrypoints, Mentimeter embeds retained, reveal/navigation, student QR and embedded teacher board');
})().catch(e=>{console.error(e);process.exit(1)});
