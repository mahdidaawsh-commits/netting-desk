const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),digest=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,'proofs',name+'.json')));
const deployment=read('deployment'),ids=['alpha-beta','alpha-gamma','beta-alpha','beta-gamma','gamma-alpha','gamma-beta'];
assert.equal(deployment.chain_id,61999);
assert.equal(deployment.source_sha256,digest(fs.readFileSync(path.join(root,'contracts/netting_desk.py'))));
assert.equal(deployment.exact_source_match,true);
assert.equal(deployment.transactions.length,5);
function net(r){return {alpha:r[2]+r[4]-r[0]-r[1],beta:r[0]+r[5]-r[2]-r[3],gamma:r[1]+r[3]-r[4]-r[5]};}
function optimum(caps){
 let best=[0,0,0,0,0,0],gross=0;
 // Six-dimensional independent enumeration, unlike the four-dimensional contract.
 function visit(r){
  if(r.length<6){for(let value=0;value<=caps[r.length];value++)visit([...r,value]);return;}
  if(Object.values(net(r)).some(value=>value!==0))return;
  const sum=r.reduce((a,b)=>a+b,0);
  const first=r.findIndex((value,i)=>value!==best[i]);
  if(sum>gross||(sum===gross&&first>=0&&r[first]>best[first])){best=r;gross=sum;}
 }
 visit([]);return best;
}
for(const [index,tx] of deployment.transactions.entries()){
 const receipt=read(tx.label+'-receipt');
 assert.equal(receipt.hash,tx.hash);
 assert.equal(receipt.status_name||receipt.statusName,'FINALIZED');
 assert.equal(receipt.result_name,'MAJORITY_AGREE');
 assert(['SUCCESS','FINISHED_WITH_RETURN'].includes(receipt.txExecutionResultName||receipt.consensus_data.leader_receipt[0].execution_result));
 assert(Object.values(receipt.consensus_data.votes).filter(value=>value==='agree').length>=3);
 if(tx.action==='deploy')continue;
 assert.equal(tx.action,'clear');
 const proof=read(tx.label),state=proof.state;
 assert.equal(state.batches.length,index);
 assert.equal(state.source_repository,'mahdidaawsh-commits/netting-desk');
 assert.equal(proof.contract_address,deployment.contract_address);
 assert.equal(proof.source_sha256,deployment.source_sha256);
 assert.equal(receipt.to_address.toLowerCase(),deployment.contract_address.toLowerCase());
 assert(receipt.data.calldata.readable.includes(state.batches.at(-1).url));
 assert(receipt.data.calldata.readable.includes(state.batches.at(-1).sha256));
 for(const batch of state.batches){
  const name=new URL(batch.url).pathname.split('/').pop().replace('.json','');
  const body=fs.readFileSync(path.join(root,'records',name+'.json')),record=JSON.parse(body);
  assert.equal(digest(body),batch.sha256);assert.deepEqual(batch.record,record);
  assert.equal(batch.url,`https://raw.githubusercontent.com/${state.source_repository}/${deployment.fixture_revision}/records/${name}.json`);
  const rows=batch.report.permissions;
  assert.deepEqual(rows.map(row=>row.id),ids);
  const decisions=ids.map((_,i)=>i===4&&name==='protected'?'DENY':i===4&&name==='conditional'?'UNKNOWN':'ALLOW');
  assert.deepEqual(rows.map(row=>row.decision),decisions);
  for(const [i,row] of rows.entries())assert(record.positions[i].clause.includes(row.quote)&&row.quote.length>=12);
  const amounts=record.positions.map(row=>row.amount),caps=amounts.map((amount,i)=>decisions[i]==='ALLOW'?amount:0);
  const reduction=optimum(caps),remaining=amounts.map((amount,i)=>amount-reduction[i]),result=batch.result;
  assert.deepEqual(result.reductions,reduction);assert.deepEqual(result.remaining,remaining);
  assert.deepEqual(result.net_before,net(amounts));assert.deepEqual(result.net_after,net(remaining));assert.deepEqual(result.net_after,result.net_before);
  const total=amounts.reduce((a,b)=>a+b,0),after=remaining.reduce((a,b)=>a+b,0);
  assert.equal(result.gross_before,total);assert.equal(result.gross_after,after);assert.equal(result.canceled_gross,total-after);
  const excluded=ids.flatMap((id,i)=>amounts[i]&&decisions[i]!=='ALLOW'?[{id,reason:decisions[i]}]:[]);
  assert.deepEqual(result.excluded,excluded);
  assert.equal(result.status,!after?'CLOSED':total>after?'NETTED':excluded.some(row=>row.reason==='UNKNOWN')?'REVIEW':'UNCHANGED');
 }
 console.log('VERIFIED',tx.label,JSON.stringify(state.batches.at(-1).result));
}
console.log('Verified five finalized receipts, independently enumerated optimal reductions and conservation of every net position.');
