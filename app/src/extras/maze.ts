import type {ExtrasData,ExtrasState,MazeRoute} from './types';
export function routeMaze(data:ExtrasData,s:ExtrasState,route:MazeRoute):ExtrasState {
 const page=data.pages.find(p=>p.id===route.page);if(!page)throw new Error('Missing original maze route');
 const node=data.maze?.nodes[route.page];if(!node&&route.page!=='maze-menu')throw new Error('Missing original maze section');
 return {...s,pageId:route.page,focus:route.focus,maze:node?{lives:node.lives,docking:node.docking}:null,
  context:node?.victory?{...s.context,randomized:false}:s.context,
  ...(route.page===s.pageId?{}:{sceneToken:s.sceneToken+1,ready:false})};
}
export function startMaze(data:ExtrasData,s:ExtrasState):ExtrasState {
 if(!data.maze)throw new Error('Missing original maze');return routeMaze(data,s,data.maze.entry);
}
