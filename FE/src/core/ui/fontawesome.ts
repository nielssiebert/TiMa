import type { App } from 'vue'
import { library } from '@fortawesome/fontawesome-svg-core'
import {
  faBars,
  faCheck,
  faCircleInfo,
  faFloppyDisk,
  faGripLines,
  faPen,
  faPlus,
  faTrash,
  faXmark,
} from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

library.add(faBars, faCheck, faCircleInfo, faFloppyDisk, faGripLines, faPen, faPlus, faTrash, faXmark)

export function registerFontAwesome(app: App): void {
  app.component('FontAwesomeIcon', FontAwesomeIcon)
}
