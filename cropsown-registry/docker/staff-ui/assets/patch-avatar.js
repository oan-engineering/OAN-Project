const fs = require('fs');
const path = require('path');

const chunkDir = '/app/.next/static/chunks';
const targetString = 'l=f.record_image_url?(0,r.jsx)("img",{src:f.record_image_url,alt:f.record_name,className:"w-12 h-12 sm:w-14 sm:h-14 lg:w-16 lg:h-16 rounded-md object-cover shrink-0"}):(0,r.jsx)("div",{className:"w-12 h-12 sm:w-14 sm:h-14 lg:w-16 lg:h-16 bg-secondary-third rounded-md shrink-0"})';
const replacementString = 'l=(0,r.jsx)("img",{src:(f.record_image_url?f.record_image_url.replace("minio:9000","localhost:9022"):"/images/register/profile.png"),onError:e=>{e.target.onerror=null;e.target.src="/images/register/profile.png"},alt:"",className:"w-12 h-12 sm:w-14 sm:h-14 lg:w-16 lg:h-16 rounded-md object-cover shrink-0"})';

function walkDir(dir) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        const filePath = path.join(dir, file);
        const stat = fs.statSync(filePath);
        if (stat.isDirectory()) {
            walkDir(filePath);
        } else if (filePath.endsWith('.js')) {
            let content = fs.readFileSync(filePath, 'utf8');
            if (content.includes(targetString)) {
                content = content.replace(targetString, replacementString);
                fs.writeFileSync(filePath, content, 'utf8');
                console.log(`Successfully patched: ${filePath}`);
                return true;
            }
        }
    }
    return false;
}

if (!walkDir(chunkDir)) {
    console.error('Target string not found in any chunks!');
    process.exit(1);
}
