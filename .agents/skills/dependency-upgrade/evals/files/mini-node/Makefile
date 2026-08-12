check:
	node test.js
	node -e "const p=require('./package.json'); if(!p.dependencies) throw new Error('no deps'); console.log('check ok', Object.keys(p.dependencies).join(','))"
