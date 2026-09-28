        struct GroundCase {float x,z,ceiling,height;bool found;};
        const GroundCase cases[]={{175.729f,-14.110f,41.5f,20.5f,true},{175,-55,20.4f,0,false},
            {175,-55,20.5f,20.5f,true},{103,17,20,12.7536954f,true},{103,17,12,0,false},
            {63,-134,40,0,false},{0,-190,40,0,true},{219,32,40,0,false}};
        for(int i=0;i<8;i++){const auto& c=cases[i];float height=-98765;
            auto* tri=mapMgr->getStaticGroundBelow(c.x,c.z,c.ceiling,height);
            require(bool(tri)==c.found,"bounded source ground presence");
            if(tri)require(std::fabs(height-c.height)<.02f && tri->mTriangle.mNormal.y>0,"bounded source ground height/normal");
            else require(height==-98765,"missing ground invented a height");
            std::printf("P2_DONUT_GROUND_CASE id=%d found=%d height=%.5f\n",i,int(bool(tri)),height);
        }
        float oldHeight=mapMgr->getMinY(175.729f,-14.110f,true);
        require(oldHeight>119 && oldHeight<121,"baseline overlapping high face");
        MoveTrace wall(Vector3f(200,45,45),Vector3f(-10,0,-20),5,true);
        mapMgr->traceMove(nullptr,wall,1.f);
        float signedWall=-.4227628f*wall.mPosition.x-.00005376f*(wall.mPosition.y+5)+.9062404f*wall.mPosition.z+52.104539f;
        std::printf("P2_DONUT_WALL x=%.5f y=%.5f z=%.5f front=%.5f\n",wall.mPosition.x,wall.mPosition.y,wall.mPosition.z,signedWall);
        require(std::isfinite(signedWall) && signedWall>=4.9f,"static tall wall trace was bypassed");
        std::puts("P2_DONUT_GROUND_QUERY bounded=8 overhead_rejected=1 wall_blocked=1");
